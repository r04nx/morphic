"""
agents/report_generator.py
--------------------------
Generates an ObseraSEC-format security report from Morphic's incident RCA data.

Steps:
  1. Fetch last 5 incidents with rca_json from PostgreSQL.
  2. Transform into the exact JSON schema used by demo_report_data.json.
  3. Save to C:/Users/User/obserasec-report-suite/public/morphic_report_data.json.
  4. Return: http://localhost:8081/?dataUrl=/morphic_report_data.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2.extras

from config import Config
from db import postgres

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output destination
# ---------------------------------------------------------------------------

_REPORT_DIR  = Path(r"C:\Users\User\obserasec-report-suite\public")
_REPORT_FILE = _REPORT_DIR / "morphic_report_data.json"
_REPORT_URL  = "http://localhost:8081/?dataUrl=/morphic_report_data.json"

# ---------------------------------------------------------------------------
# Mapping constants
# ---------------------------------------------------------------------------

_BLAST_TO_SEVERITY = {
    "CRITICAL": "Critical",
    "HIGH":     "High",
    "MEDIUM":   "Medium",
    "LOW":      "Low",
}

_BLAST_TO_COLOR = {
    "CRITICAL": "hsl(0, 84%, 60%)",
    "HIGH":     "hsl(25, 95%, 53%)",
    "MEDIUM":   "hsl(45, 93%, 47%)",
    "LOW":      "hsl(142, 71%, 45%)",
}

# The five target bug types
_BUG_TYPES = [
    "Gateway Timeout",
    "Partial Write",
    "Race Condition",
    "Async Trace Loss",
    "Inconsistent Order State",
]

# Keyword → bug type
_BUG_KEYWORD_MAP = {
    "gateway":   "Gateway Timeout",
    "timeout":   "Gateway Timeout",
    "duplicate": "Gateway Timeout",
    "partial":   "Partial Write",
    "orphan":    "Partial Write",
    "race":      "Race Condition",
    "stock":     "Race Condition",
    "inventory": "Race Condition",
    "async":     "Async Trace Loss",
    "mdc":       "Async Trace Loss",
    "trace":     "Async Trace Loss",
    "order":     "Inconsistent Order State",
    "stuck":     "Inconsistent Order State",
    "created":   "Inconsistent Order State",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_bug(incident: dict) -> str:
    text = (
        (incident.get("classification") or "") + " " +
        (incident.get("root_cause") or "")
    ).lower()
    for kw, bt in _BUG_KEYWORD_MAP.items():
        if kw in text:
            return bt
    return "Inconsistent Order State"


def _fetch_incidents(limit: int = 5) -> list[dict]:
    """Fetch last N incidents that have an rca_json from PostgreSQL."""
    sql = """
        SELECT id, trace_id, timestamp, classification, root_cause,
               blast_radius, impact, confidence_score, status, service,
               summary, rca_json, created_at, updated_at
        FROM incidents
        WHERE rca_json IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT %s
    """
    try:
        with postgres.get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            rj = d.get("rca_json")
            if isinstance(rj, str):
                try:
                    d["rca_json"] = json.loads(rj)
                except Exception:
                    d["rca_json"] = {}
            result.append(d)
        return result
    except Exception as exc:
        logger.error("fetch_incidents failed: %s", exc)
        return []


def _build_finding(idx: int, incident: dict, rca: dict) -> dict:
    """Map one incident + RCA to an ObseraSEC finding entry."""
    blast     = (incident.get("blast_radius") or "MEDIUM").upper()
    severity  = _BLAST_TO_SEVERITY.get(blast, "Medium")
    confidence= float(incident.get("confidence_score") or 0.5)
    cvss      = round(min(confidence * 10, 10.0), 1)
    bug_type  = _classify_bug(incident)
    service   = incident.get("service") or rca.get("log_signals", {}).get("service", "backend-service")
    trace_id  = incident.get("trace_id", "")
    fix       = rca.get("suggested_fix", {})
    signals   = rca.get("log_signals", {})
    ts        = incident.get("created_at")
    ts_str    = ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")

    return {
        "id":       f"MORF-F{str(idx).zfill(3)}",
        "title":    incident.get("classification") or rca.get("classification") or bug_type,
        "severity": severity,
        "cvss":     cvss,
        "category": bug_type,
        "affectedHosts": [service],
        "description": (
            rca.get("root_cause")
            or incident.get("root_cause")
            or f"{bug_type} detected in {service}"
        ),
        "impact": (
            rca.get("impact")
            or incident.get("impact")
            or f"Service degradation in {service}"
        ),
        "evidence": (
            f"trace_id: {trace_id}\n"
            f"service: {signals.get('service', service)}\n"
            f"endpoint: {signals.get('endpoint', 'N/A')}\n"
            f"exception: {signals.get('exception_class', 'N/A')}\n"
            f"error: {signals.get('error_message', 'N/A')}\n"
            f"detected_at: {ts_str}"
        ),
        "remediation": (
            fix.get("patch")
            or fix.get("rationale")
            or f"Apply fix to {fix.get('target_class', service)}"
        ),
        "references": [
            f"trace_id:{trace_id}",
            f"Morphic RCA — confidence {cvss}/10",
            f"target_class:{fix.get('target_class', 'N/A')}",
        ],
        "cve": f"MORF-{trace_id[:8].upper()}" if trace_id else f"MORF-F{str(idx).zfill(3)}",
    }


def _build_remediation_roadmap(findings: list[dict]) -> dict:
    immediate, short_term, long_term = [], [], []
    effort_map   = {"Critical": "High", "High": "Medium", "Medium": "Low", "Low": "Low"}
    deadline_map = {"Critical": "24 hours", "High": "1 week", "Medium": "2 weeks", "Low": "4 weeks"}

    for f in findings:
        sev = f["severity"]
        entry = {
            "finding":  f["id"],
            "action":   f"Remediate {f['category']} in {f['affectedHosts'][0] if f['affectedHosts'] else 'service'}",
            "effort":   effort_map.get(sev, "Medium"),
            "impact":   sev,
            "deadline": deadline_map.get(sev, "4 weeks"),
        }
        if sev == "Critical":
            immediate.append(entry)
        elif sev == "High":
            short_term.append(entry)
        else:
            long_term.append(entry)

    return {"immediate": immediate, "shortTerm": short_term, "longTerm": long_term}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_report() -> str:
    """
    Build the full Morphic incident report in ObseraSEC JSON format.
    Saves to morphic_report_data.json and returns the viewer URL.
    """
    incidents = _fetch_incidents(limit=5)
    now       = datetime.now(timezone.utc)
    date_str  = now.strftime("%d %B %Y").lstrip("0")

    # --- Aggregate counts ---
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    scores: list[float]    = []
    for inc in incidents:
        br = (inc.get("blast_radius") or "MEDIUM").upper()
        counts[br] = counts.get(br, 0) + 1
        scores.append(float(inc.get("confidence_score") or 0.5))

    total          = len(incidents)
    avg_confidence = (sum(scores) / len(scores)) if scores else 0.5
    risk_score     = round(avg_confidence * 10, 1)

    # --- Findings ---
    findings = [
        _build_finding(i + 1, inc, inc.get("rca_json") or {})
        for i, inc in enumerate(incidents)
    ]

    # --- Bug type distribution ---
    bug_counts: dict[str, int] = {bt: 0 for bt in _BUG_TYPES}
    for inc in incidents:
        bug_counts[_classify_bug(inc)] += 1
    category_dist = [{"category": k, "count": v} for k, v in bug_counts.items()]

    # --- Severity distribution ---
    severity_dist = [
        {"name": "Critical", "value": counts["CRITICAL"], "color": _BLAST_TO_COLOR["CRITICAL"]},
        {"name": "High",     "value": counts["HIGH"],     "color": _BLAST_TO_COLOR["HIGH"]},
        {"name": "Medium",   "value": counts["MEDIUM"],   "color": _BLAST_TO_COLOR["MEDIUM"]},
        {"name": "Low",      "value": counts["LOW"],      "color": _BLAST_TO_COLOR["LOW"]},
        {"name": "Info",     "value": 0,                  "color": "hsl(210, 80%, 55%)"},
    ]

    # --- Risk trend (6 months leading to now) ---
    month_labels = ["Nov 25", "Dec 25", "Jan 26", "Feb 26", "Mar 26", "Apr 26"]
    base = max(risk_score - 2.5, 1.0)
    risk_trend = [
        {"month": m, "score": round(base + i * (risk_score - base) / 5, 1)}
        for i, m in enumerate(month_labels)
    ]
    risk_trend[-1]["score"] = risk_score

    # --- Service-level summary ---
    svc_map: dict[str, dict] = {}
    for inc in incidents:
        svc = inc.get("service") or "backend-service"
        br  = (inc.get("blast_radius") or "LOW").lower()
        if svc not in svc_map:
            svc_map[svc] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        if br in svc_map[svc]:
            svc_map[svc][br] += 1
    host_summary = [{"host": svc, **cnts} for svc, cnts in svc_map.items()]

    # --- Entity graph ---
    entity_nodes: list[dict] = [{"id": "morphic-core", "label": "Morphic AI", "type": "platform"}]
    entity_edges: list[dict] = []
    seen_nodes: set[str]     = {"morphic-core"}

    for inc in incidents:
        svc    = inc.get("service") or "backend"
        tid    = (inc.get("trace_id") or "")[:8]
        rca    = inc.get("rca_json") or {}
        fix    = rca.get("suggested_fix") or {}
        inc_id = f"inc-{tid}"
        svc_id = f"svc-{svc}"

        if inc_id not in seen_nodes:
            entity_nodes.append({
                "id": inc_id,
                "label": inc.get("classification") or tid,
                "type": "incident",
                "blast_radius": inc.get("blast_radius", "LOW"),
            })
            seen_nodes.add(inc_id)
        if svc_id not in seen_nodes:
            entity_nodes.append({"id": svc_id, "label": svc, "type": "service"})
            seen_nodes.add(svc_id)

        entity_edges.append({"from": "morphic-core", "to": inc_id, "label": "detected"})
        entity_edges.append({"from": inc_id, "to": svc_id, "label": "in"})

        if fix.get("target_class"):
            cls_id = f"cls-{fix['target_class']}"
            if cls_id not in seen_nodes:
                entity_nodes.append({"id": cls_id, "label": fix["target_class"], "type": "javaClass"})
                seen_nodes.add(cls_id)
            entity_edges.append({"from": inc_id, "to": cls_id, "label": "caused by"})

    # --- Compliance mapping ---
    pass_fail = lambda ok: "Pass" if ok else "Fail"
    compliance_mapping = {
        "frameworks": [
            {
                "name": "DORA (Digital Ops Resilience)",
                "score": min(100, int(avg_confidence * 100)),
                "controls": [
                    {"control": "Art.9",  "title": "ICT Risk Management",        "status": pass_fail(avg_confidence > 0.7), "finding": findings[0]["id"] if findings else "-"},
                    {"control": "Art.10", "title": "Incident Classification",     "status": "Pass",                         "finding": "-"},
                    {"control": "Art.17", "title": "Operational Resilience Test", "status": "Partial",                      "finding": findings[-1]["id"] if findings else "-"},
                ],
            },
            {
                "name": "SRE Golden Signals",
                "score": min(100, int(avg_confidence * 95)),
                "controls": [
                    {"control": "Latency",    "title": "Request Latency",     "status": pass_fail(counts["CRITICAL"] == 0), "finding": "-"},
                    {"control": "Errors",     "title": "Error Rate",          "status": pass_fail(total == 0),              "finding": findings[0]["id"] if findings else "-"},
                    {"control": "Traffic",    "title": "Throughput",          "status": "Pass",                             "finding": "-"},
                    {"control": "Saturation", "title": "Resource Saturation", "status": "Partial",                          "finding": "-"},
                ],
            },
            {
                "name": "CIS Controls v8",
                "score": min(100, int(avg_confidence * 88)),
                "controls": [
                    {"control": "8",  "title": "Audit Log Management",  "status": "Pass",                                  "finding": "-"},
                    {"control": "16", "title": "Application Security",  "status": pass_fail(counts["CRITICAL"] == 0),      "finding": findings[0]["id"] if findings else "-"},
                    {"control": "7",  "title": "Vulnerability Mgmt",   "status": pass_fail(total < 3),                    "finding": "-"},
                ],
            },
        ]
    }

    resolved   = [i for i in incidents if i.get("status") in ("resolved", "healed")]
    open_incs  = [i for i in incidents if i.get("status") not in ("resolved", "healed")]

    # --- Assemble full report ---
    report: dict[str, Any] = {
        "meta": {
            "title":          "AI-Driven Incident Intelligence Report",
            "subtitle":       "Automated Root Cause Analysis & Self-Healing Assessment",
            "client":         "Morphic AI — Self-Healing Incident Assistant",
            "clientIndustry": "Platform Engineering / SRE",
            "assessmentId":   f"MORF-{now.strftime('%Y-%m')}",
            "version":        "1.0",
            "classification": "INTERNAL",
            "date":           date_str,
            "dateRange":      f"Last {total} resolved incident(s) as of {date_str}",
            "preparedBy":     "Morphic AI — Automated RCA Engine",
            "platform":       "Morphic",
            "company":        "Morphic AI",
            "logoUrl":        "https://flem.xo.je/uploads/image_1ab47d1d.png",
            "coverUrl":       "/assets/cover_bg.png",
        },
        "docControl": {
            "versions": [
                {"version": "1.0", "date": now.strftime("%Y-%m-%d"),
                 "author": "Morphic AI Engine", "changes": "Auto-generated from live incident data"}
            ],
            "authors":      [{"name": "Morphic AI",    "role": "Automated RCA Engine",   "email": "morphic@ai"}],
            "reviewers":    [{"name": "On-call SRE",   "role": "Incident Reviewer",      "email": "sre@team"}],
            "distribution": [{"name": "Engineering Team", "role": "Morphic Platform Users"}],
        },
        "execSummary": {
            "totalVulnerabilities": total,
            "critical":             counts["CRITICAL"],
            "high":                 counts["HIGH"],
            "medium":               counts["MEDIUM"],
            "low":                  counts["LOW"],
            "informational":        0,
            "overallRiskScore":     risk_score,
            "systemsTested":        max(len(svc_map), 1),
            "systemsCompromised":   counts["CRITICAL"] + counts["HIGH"],
            "riskStatement": (
                f"Morphic AI detected and analysed {total} incident(s) in the HackathonPS chaos backend. "
                f"{counts['CRITICAL']} CRITICAL and {counts['HIGH']} HIGH severity incidents were identified. "
                f"The average AI confidence score maps to an overall risk score of {risk_score}/10. "
                f"All incidents relate to the five core failure scenarios: Gateway Timeout → Duplicate Payment, "
                f"Partial Write → Orphaned Record, Race Condition → Negative Stock, "
                f"Async Trace Loss → MDC Failure, Inconsistent Order State → Stuck CREATED. "
                f"Automated remediations (email alerts + GitHub PRs with surgical Java patches) were triggered "
                f"for HIGH and CRITICAL incidents. {len(resolved)} incident(s) confirmed healed."
            ),
        },
        "toc": [
            {"num": "1",   "title": "Executive Summary",             "page": 4},
            {"num": "1.1", "title": "Key Metrics Overview",          "page": 4},
            {"num": "1.2", "title": "Risk Assessment Score",         "page": 5},
            {"num": "1.3", "title": "Executive Risk Statement",      "page": 6},
            {"num": "2",   "title": "Scope & Methodology",           "page": 7},
            {"num": "3",   "title": "Risk Summary Dashboard",        "page": 9},
            {"num": "4",   "title": "Incident Architecture Overview","page": 12},
            {"num": "5",   "title": "Detailed Findings (RCA)",       "page": 16},
            {"num": "6",   "title": "Vulnerability Trending",        "page": 28},
            {"num": "7",   "title": "Compliance Mapping",            "page": 30},
            {"num": "8",   "title": "Remediation Roadmap",           "page": 36},
            {"num": "9",   "title": "Entity Relationship Graph",     "page": 40},
        ],
        "severityDist":  severity_dist,
        "categoryDist":  category_dist,
        "riskTrend":     risk_trend,
        "hostSummary":   host_summary,
        "hostFindings":  host_summary,
        "scope": {
            "ipRanges": [
                {"range": "hackathonps-ykxr.onrender.com", "description": "Chaos Backend (Spring Boot)", "hosts": 1},
                {"range": "localhost:5000",                 "description": "Morphic Flask Backend",       "hosts": 1},
                {"range": "localhost:3000",                 "description": "Morphic React Dashboard",     "hosts": 1},
            ],
            "tools": [
                {"name": "Anthropic Claude",  "version": Config.ANTHROPIC_MODEL, "purpose": "AI Root Cause Analysis"},
                {"name": "Morphic Ingestion", "version": "1.0",                  "purpose": "Log polling & dedup (30s interval)"},
                {"name": "Morphic Triage",    "version": "1.0",                  "purpose": "Severity classification"},
                {"name": "GitHub REST API",   "version": "v3",                   "purpose": "Java source fetch & PR creation"},
                {"name": "PostgreSQL",        "version": "16",                   "purpose": "Incident + RCA persistence"},
                {"name": "Neo4j",             "version": "5",                    "purpose": "Incident graph relationships"},
                {"name": "Redis",             "version": "7",                    "purpose": "Dedup watermarks"},
            ],
            "timeline": [
                {"phase": "Log Ingestion", "start": 1, "duration": 1},
                {"phase": "Triage",        "start": 1, "duration": 1},
                {"phase": "GitHub Fetch",  "start": 2, "duration": 1},
                {"phase": "RCA (Claude)",  "start": 2, "duration": 2},
                {"phase": "Remediation",   "start": 4, "duration": 1},
                {"phase": "Notification",  "start": 5, "duration": 1},
            ],
        },
        "networkAssets": [
            {
                "ip":       inc.get("service") or "backend-service",
                "hostname": (inc.get("trace_id") or "")[:12],
                "os":       "Spring Boot 3.x / JVM 21",
                "type":     _classify_bug(inc),
                "ports":    "8080, 443",
                "vulns":    1,
                "risk":     _BLAST_TO_SEVERITY.get((inc.get("blast_radius") or "MEDIUM").upper(), "Medium"),
            }
            for inc in incidents
        ],
        "subnets": [
            {"subnet": "chaos-backend",   "name": "HackathonPS Service", "vlan": "prod",  "hosts": 1, "gateway": "render.com"},
            {"subnet": "morphic-backend", "name": "Morphic Flask API",   "vlan": "local", "hosts": 1, "gateway": "localhost"},
            {"subnet": "morphic-ui",      "name": "Morphic Dashboard",   "vlan": "local", "hosts": 1, "gateway": "localhost"},
        ],
        "geoData": {
            "attackOrigins": [
                {"country": "Internal Chaos Scheduler", "attacks": total, "lat": 28.6, "lng": 77.2},
            ],
            "totalBlocked": len(resolved),
            "uniqueIPs":    1,
            "c2Servers":    0,
        },
        "findings": findings,
        "trending": {
            "byPhase": [
                {"phase": "Ingested",   "discovered": total},
                {"phase": "Triaged",    "discovered": total},
                {"phase": "RCA Done",   "discovered": len([i for i in incidents if i.get("rca_json")])},
                {"phase": "Remediated", "discovered": len(resolved)},
            ],
            "byService": [
                {
                    "service":  svc,
                    "critical": cnts["critical"],
                    "high":     cnts["high"],
                    "medium":   cnts["medium"],
                    "low":      cnts["low"],
                }
                for svc, cnts in svc_map.items()
            ],
            "patchStatus": [
                {"name": "Healed", "value": len(resolved)},
                {"name": "Open",   "value": len(open_incs)},
            ],
            "riskExposure": [
                {"day": f"Inc {i + 1}", "exposure": round(float(inc.get("confidence_score") or 0.5) * 100)}
                for i, inc in enumerate(incidents)
            ],
        },
        "remediation": _build_remediation_roadmap(findings),
        "complianceMapping": compliance_mapping,
        "compliance": {
            "dpdp": {
                "privacyScore":       100,
                "complianceStatus":   "Compliant",
                "gapCount":           0,
                "dsrEfficiency":      "N/A",
                "applicabilityTitle": "No PII Processed",
                "applicabilityText":  "Morphic processes only system logs and incident metadata — no personal data.",
                "consentTotalLabel":  "N/A",
                "consentMetrics":     [],
                "dsrMetrics":         [],
                "piiInventoryTitle":  "Operational Telemetry Only",
                "piiInventory": [
                    {"category": "Incident Logs", "type": "trace_id, timestamps, log messages",
                     "lawfulBasis": "Operational", "exposure": "Low"},
                ],
                "complianceMatrix": [
                    {"section": "Data Processing", "status": "Compliant",
                     "remarks": "Only operational telemetry — no PII stored or transmitted."},
                ],
            },
            "certin": {
                "assetsScanned": total,
                "vulnerabilitySummary": [s for s in severity_dist if s["value"] > 0],
                "auditScope": [
                    {"type": "Spring Boot Microservice", "count": 1,
                     "methodology": "AI Log Analysis + GitHub Source Review"},
                    {"type": "Async Threads / MDC",      "count": 1,
                     "methodology": "Automated Trace Correlation"},
                ],
                "topVulnerabilities": [
                    {
                        "title":    f["title"],
                        "cve":      f["cve"],
                        "severity": f["severity"],
                        "asset":    f["affectedHosts"][0] if f["affectedHosts"] else "N/A",
                        "status":   "Resolved" if incidents[i].get("status") in ("resolved", "healed") else "Open",
                    }
                    for i, f in enumerate(findings[:3])
                ],
                "trendData": [
                    {"month": pt["month"], "vulns": max(1, int(pt["score"]))}
                    for pt in risk_trend
                ],
            },
            "sebi": {
                "governanceScore": 90, "rbiMasterDirectionStatus": "N/A",
                "sebiCscrfStatus": "N/A", "riskHeatmap": [], "controlGaps": [],
            },
            "rbi": {
                "governanceScore": 90, "rbiMasterDirectionStatus": "N/A",
                "sebiCscrfStatus": "N/A", "riskHeatmap": [], "controlGaps": [],
            },
        },
        "portScan": [
            {"ip": "hackathonps-ykxr.onrender.com", "port": 443,  "protocol": "HTTPS",
             "service": "Spring Boot", "version": "3.x", "state": "Open"},
            {"ip": "localhost",                      "port": 5000, "protocol": "HTTP",
             "service": "Morphic Flask", "version": "3.0.3", "state": "Open"},
            {"ip": "localhost",                      "port": 3000, "protocol": "HTTP",
             "service": "Morphic React", "version": "Vite", "state": "Open"},
        ],
        "riskMatrix": [
            ["",              "Negligible", "Minor",   "Moderate", "Major", "Catastrophic"],
            ["Almost Certain","M",          "H",       "H",        "C",     "C"],
            ["Likely",        "M",          "M",       "H",        "H",     "C"],
            ["Possible",      "L",          "M",       "M",        "H",     "H"],
            ["Unlikely",      "L",          "L",       "M",        "M",     "H"],
            ["Rare",          "L",          "L",       "L",        "M",     "M"],
        ],
        "entityGraph": {
            "nodes": entity_nodes,
            "edges": entity_edges,
        },
    }

    # --- Write to disk ---
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Report saved to %s (%d incidents, risk=%.1f)", _REPORT_FILE, total, risk_score)

    return _REPORT_URL
