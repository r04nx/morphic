"""
Orchestrator Agent — Coordinates the full pipeline.

Runs as a background thread (APScheduler job) every 30 seconds:
  ingest → triage → rca → remediate → notify

Errors in any stage are caught and logged; the loop never crashes.
"""

import logging
from typing import Any

from config import Config
from agents import ingestion, triage, rca as rca_agent, remediation, notification, github_pr

logger = logging.getLogger(__name__)


def _process_incident(incident: dict[str, Any]) -> None:
    """Run the full pipeline for a single new incident."""
    trace_id = incident.get("trace_id", "unknown")
    logger.info("=== Processing incident trace_id=%s ===", trace_id)

    # -------------------------------------------------------
    # Layer 1.5: Triage
    # -------------------------------------------------------
    try:
        triage_result = triage.classify(incident)
    except Exception as exc:
        logger.error("Triage failed for trace_id=%s: %s", trace_id, exc)
        return

    incident["triage_classification"] = triage_result["classification"]
    incident["triage_blast_radius"]   = triage_result["blast_radius"]

    if not triage_result["needs_rca"]:
        reason = triage_result.get("suppression_reason") or "below severity threshold"
        logger.info("Skipping RCA for trace_id=%s — %s", trace_id, reason)
        return

    # -------------------------------------------------------
    # Layer 2: RCA
    # -------------------------------------------------------
    rca_result: dict[str, Any] | None = None
    try:
        rca_result = rca_agent.run_rca(incident)
    except Exception as exc:
        logger.error("RCA failed for trace_id=%s: %s", trace_id, exc)

    if not rca_result:
        logger.warning("No RCA produced for trace_id=%s — alerting with triage data", trace_id)
        # Build a minimal RCA so notification still works
        rca_result = {
            "trace_id":        trace_id,
            "timestamp":       str(incident.get("timestamp", "")),
            "classification":  triage_result["classification"],
            "blast_radius":    triage_result["blast_radius"],
            "root_cause":      incident.get("message", "")[:300],
            "impact":          "Impact analysis unavailable — RCA agent error",
            "log_signals":     {
                "service":         incident.get("service", ""),
                "endpoint":        incident.get("endpoint", ""),
                "exception_class": incident.get("exception", ""),
                "error_message":   incident.get("message", "")[:200],
            },
            "suggested_fix":  {},
            "github_pr":      {},
            "confidence_score": 0.3,
        }

    # -------------------------------------------------------
    # Layer 3: Remediation decision
    # -------------------------------------------------------
    remediation_result: dict[str, Any] = {}
    try:
        remediation_result = remediation.plan_and_execute(incident, rca_result)
    except Exception as exc:
        logger.error("Remediation planning failed for trace_id=%s: %s", trace_id, exc)

    # -------------------------------------------------------
    # Layer 3: GitHub PR (if planned)
    # -------------------------------------------------------
    pr_url: str | None = None
    if "github_pr" in remediation_result.get("planned_actions", []):
        try:
            pr_result = github_pr.create_pr(
                incident,
                rca_result,
                incident_id=incident.get("incident_id"),
                dashboard_url=Config.DASHBOARD_URL,
            )
            if pr_result.get("success"):
                pr_url = pr_result.get("pr_url")
                logger.info("PR created: %s", pr_url)
            else:
                logger.warning("PR creation failed: %s", pr_result.get("error"))
        except Exception as exc:
            logger.error("GitHub PR agent error for trace_id=%s: %s", trace_id, exc)

    # -------------------------------------------------------
    # Layer 3: Email notification (always, if email is planned)
    # -------------------------------------------------------
    if "email" in remediation_result.get("planned_actions", ["email"]):
        try:
            notification.send_alert(rca_result, incident, pr_url=pr_url)
        except Exception as exc:
            logger.error("Notification failed for trace_id=%s: %s", trace_id, exc)

    logger.info("=== Pipeline complete for trace_id=%s ===", trace_id)


def run_pipeline() -> None:
    """
    Single orchestration cycle.
    Called by APScheduler every POLL_INTERVAL_SECONDS seconds.
    """
    logger.info("Orchestrator cycle starting")
    try:
        new_incidents = ingestion.run_ingestion()
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        return

    if not new_incidents:
        logger.debug("No new incidents this cycle")
        return

    logger.info("Processing %d new incidents", len(new_incidents))
    for incident in new_incidents:
        try:
            _process_incident(incident)
        except Exception as exc:
            logger.error(
                "Unhandled error processing trace_id=%s: %s",
                incident.get("trace_id", "?"),
                exc,
            )

    logger.info("Orchestrator cycle complete")
