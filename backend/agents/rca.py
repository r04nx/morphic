"""
RCA Agent — Layer 2 (Intelligence Layer)
Calls Anthropic Claude to produce a strict JSON RCA document.
After RCA, updates PostgreSQL and Neo4j with the result.
"""

import json
import logging
import re
from typing import Any

import anthropic

from config import Config
from db import postgres, neo4j_client

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a senior Site Reliability Engineer (SRE) specializing in distributed systems,
Java Spring Boot microservices, and production incident management.

Your job is to analyze structured log data and produce a precise Root Cause Analysis (RCA).

CRITICAL RULES:
1. You MUST return ONLY a valid JSON object — no prose, no markdown, no code fences.
2. The JSON must strictly match the schema provided.
3. The suggested_fix.target_class MUST reference the actual Java class name present in the logs.
4. Do NOT guess or hallucinate class names — use only what appears in the log data.
5. blast_radius must be exactly one of: LOW, MEDIUM, HIGH, CRITICAL
6. confidence_score must be a float between 0.0 and 1.0
7. suggested_fix.patch must be a real, compilable Java code snippet — not pseudocode.
8. github_pr.labels must be a JSON array of strings.

The five incident scenarios you must recognize and prioritize:
- Gateway Timeout → Duplicate Payment (idempotency failure)
- Partial Write → Orphaned Payment Record (transaction rollback missing)
- Race Condition → Negative Stock (missing synchronization / optimistic lock)
- Async Trace Loss → MDC Propagation Failure (ThreadLocal not propagated across async boundaries)
- Inconsistent Order State → Stuck CREATED (missing state machine guard)
"""

_RCA_SCHEMA = """{
  "classification": "string",
  "root_cause": "string (one sentence)",
  "blast_radius": "LOW|MEDIUM|HIGH|CRITICAL",
  "impact": "string (plain English, non-technical)",
  "trace_id": "string",
  "timestamp": "string",
  "log_signals": {
    "service": "string",
    "endpoint": "string",
    "exception_class": "string",
    "error_message": "string"
  },
  "suggested_fix": {
    "language": "java",
    "target_class": "string",
    "patch": "string (compilable Java code)",
    "rationale": "string",
    "tests": ["string"]
  },
  "github_pr": {
    "title": "string",
    "body": "string",
    "labels": ["string"]
  },
  "confidence_score": 0.0
}"""


def _build_user_prompt(incident: dict[str, Any], log_slice: list[dict[str, Any]]) -> str:
    """Compose a minimal but sufficient prompt for Claude."""
    log_text = json.dumps(log_slice, indent=2, default=str)[:8000]  # cap tokens
    return f"""Analyze the following incident and produce an RCA JSON.

=== INCIDENT METADATA ===
trace_id:      {incident.get("trace_id")}
timestamp:     {incident.get("timestamp")}
service:       {incident.get("service")}
classification:{incident.get("triage_classification", "unknown")}
blast_radius:  {incident.get("triage_blast_radius", "unknown")}
async_orphan:  {incident.get("async_orphan", False)}

=== LOG SLICE (this trace_id only) ===
{log_text}

=== REQUIRED JSON SCHEMA ===
{_RCA_SCHEMA}

Return ONLY the JSON object. No other text."""


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from Claude's response."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try to find a {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Claude returned non-JSON response: {text[:300]}")


def run_rca(incident: dict[str, Any]) -> dict[str, Any] | None:
    """
    Call Claude for a single incident.

    Args:
        incident: normalised incident dict from the ingestion/triage pipeline.
                  Must have: trace_id, timestamp, service, incident_id.

    Returns:
        Full RCA dict on success, None on failure.
    """
    trace_id = incident.get("trace_id", "unknown")
    incident_id = incident.get("incident_id")

    # Fetch the log slice for this trace from PostgreSQL
    log_slice: list[dict[str, Any]] = []
    if incident_id:
        try:
            rows = postgres.get_trace_events(trace_id, limit=50)
            log_slice = [
                {
                    "timestamp": str(r.get("timestamp")),
                    "level":     r.get("log_level"),
                    "service":   r.get("service"),
                    "endpoint":  r.get("endpoint"),
                    "message":   r.get("message"),
                    "raw":       r.get("raw_log"),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("Could not fetch trace events from DB: %s", exc)

    # Fall back to the raw field on the incident itself
    if not log_slice:
        log_slice = [
            {
                "timestamp": str(incident.get("timestamp")),
                "level":     incident.get("level"),
                "service":   incident.get("service"),
                "endpoint":  incident.get("endpoint"),
                "message":   incident.get("message"),
                "exception": incident.get("exception"),
            }
        ]

    user_prompt = _build_user_prompt(incident, log_slice)

    try:
        response = _get_client().messages.create(
            model=Config.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = response.content[0].text if response.content else ""
    except anthropic.APIConnectionError as exc:
        logger.error("Anthropic connection error for trace_id=%s: %s", trace_id, exc)
        return None
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit hit for trace_id=%s", trace_id)
        return None
    except Exception as exc:
        logger.error("Anthropic API error for trace_id=%s: %s", trace_id, exc)
        return None

    try:
        rca = _extract_json(raw_text)
    except ValueError as exc:
        logger.error("RCA JSON parse failed for trace_id=%s: %s", trace_id, exc)
        return None

    # Enforce required fields / defaults
    rca.setdefault("trace_id", trace_id)
    rca.setdefault("timestamp", str(incident.get("timestamp", "")))
    rca.setdefault("confidence_score", 0.5)
    rca.setdefault("blast_radius", incident.get("triage_blast_radius", "LOW"))
    rca.setdefault("classification", incident.get("triage_classification", "Unknown"))
    rca.setdefault("log_signals", {})
    rca.setdefault("suggested_fix", {})
    rca.setdefault("github_pr", {})

    # Validate blast_radius
    if rca["blast_radius"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        rca["blast_radius"] = "MEDIUM"

    # Clamp confidence score
    try:
        rca["confidence_score"] = max(0.0, min(1.0, float(rca["confidence_score"])))
    except (TypeError, ValueError):
        rca["confidence_score"] = 0.5

    logger.info(
        "RCA complete: trace_id=%s classification=%s blast=%s confidence=%.2f",
        trace_id,
        rca.get("classification"),
        rca.get("blast_radius"),
        rca.get("confidence_score"),
    )

    # --- Persist RCA to PostgreSQL ---
    if incident_id:
        try:
            postgres.upsert_incident({
                "trace_id":        trace_id,
                "timestamp":       incident.get("timestamp"),
                "service":         incident.get("service"),
                "classification":  rca.get("classification"),
                "root_cause":      rca.get("root_cause"),
                "blast_radius":    rca.get("blast_radius"),
                "impact":          rca.get("impact"),
                "confidence_score": rca.get("confidence_score"),
                "status":          "investigating",
                "rca_json":        rca,
                "summary":         rca.get("root_cause", "")[:500],
            })
        except Exception as exc:
            logger.error("Failed to persist RCA to PostgreSQL: %s", exc)

    # --- Update Neo4j with RCA ---
    try:
        neo4j_client.link_rca_to_incident(trace_id, rca)
        neo4j_client.update_incident_status_graph(trace_id, "investigating")
    except Exception as exc:
        logger.warning("Neo4j RCA update failed: %s", exc)

    return rca
