"""
Remediation Planner Agent — Layer 3
Decides which automated actions to run based on blast_radius and confidence_score.
Also calls the chaos backend runtime endpoints and verifies healing.
"""

import logging
import time
from typing import Any

import requests

from config import Config
from db import postgres, neo4j_client

logger = logging.getLogger(__name__)


def _chaos_post_order(fix_params: dict[str, Any]) -> dict[str, Any]:
    """POST /order on the chaos backend to apply a runtime fix."""
    url = f"{Config.CHAOS_BACKEND_URL}/order"
    try:
        resp = requests.post(url, json=fix_params, timeout=15)
        resp.raise_for_status()
        return {"ok": True, "response": resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _chaos_health_check() -> dict[str, Any]:
    """GET /health on the chaos backend to verify the fix worked."""
    url = f"{Config.CHAOS_BACKEND_URL}/health"
    try:
        resp = requests.get(url, timeout=10)
        return {"ok": resp.status_code == 200, "status_code": resp.status_code, "body": resp.text[:500]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _chaos_poll_logs(trace_id: str) -> bool:
    """
    Re-poll /logs after applying a fix and check whether the same trace_id
    is still generating errors. Returns True if the error appears to have stopped.
    """
    url = f"{Config.CHAOS_BACKEND_URL}/logs"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        logs = resp.json()
        if not isinstance(logs, list):
            logs = logs.get("logs") or []
        # Check if trace_id still appears with ERROR level
        for entry in logs:
            if (
                (entry.get("trace_id") or entry.get("traceId")) == trace_id
                and (entry.get("level") or "").upper() in {"ERROR", "FATAL"}
            ):
                return False  # still erroring
        return True  # no fresh errors for this trace_id
    except Exception:
        return False  # unknown → assume not healed


def plan_and_execute(
    incident: dict[str, Any],
    rca: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate RCA and decide + execute remediation actions.

    Decision matrix:
    - confidence < HIGH_CONFIDENCE_THRESHOLD  → alert only (no PR)
    - HIGH/CRITICAL + confidence >= threshold → alert + PR + attempt runtime fix
    - MEDIUM + confidence >= threshold        → alert + PR

    Returns a summary dict of actions triggered.
    """
    trace_id = rca.get("trace_id") or incident.get("trace_id", "unknown")
    incident_id = incident.get("incident_id")
    blast_radius = rca.get("blast_radius", "LOW")
    confidence = float(rca.get("confidence_score", 0.0))

    actions_triggered: list[str] = []
    result: dict[str, Any] = {
        "trace_id":          trace_id,
        "blast_radius":      blast_radius,
        "confidence_score":  confidence,
        "actions":           [],
        "healed":            False,
    }

    # -----------------------------------------------------------------------
    # Decision: always alert
    # -----------------------------------------------------------------------
    actions_triggered.append("email")

    # -----------------------------------------------------------------------
    # Decision: open a GitHub PR if confidence is sufficient
    # -----------------------------------------------------------------------
    wants_pr = (
        confidence >= Config.MIN_CONFIDENCE_FOR_PR
        and blast_radius in {"MEDIUM", "HIGH", "CRITICAL"}
        and rca.get("suggested_fix", {}).get("target_class")
    )
    if wants_pr:
        actions_triggered.append("github_pr")

    # -----------------------------------------------------------------------
    # Decision: attempt runtime chaos backend fix for HIGH/CRITICAL
    # -----------------------------------------------------------------------
    wants_runtime_fix = (
        blast_radius in {"HIGH", "CRITICAL"}
        and confidence >= Config.HIGH_CONFIDENCE_THRESHOLD
    )

    result["planned_actions"] = actions_triggered
    result["wants_runtime_fix"] = wants_runtime_fix

    # -----------------------------------------------------------------------
    # Execute: runtime fix via chaos backend
    # -----------------------------------------------------------------------
    if wants_runtime_fix and incident_id:
        action_row = None
        try:
            action_row = postgres.insert_action({
                "incident_id": incident_id,
                "action_type": "runtime_fix",
                "status":      "running",
                "details":     {"trace_id": trace_id, "blast_radius": blast_radius},
            })
        except Exception as exc:
            logger.warning("Could not record runtime_fix action: %s", exc)

        fix_result = _chaos_post_order({"trace_id": trace_id, "action": "remediate"})
        time.sleep(5)  # brief wait before verification
        health = _chaos_health_check()
        healed = health.get("ok", False)

        if not healed:
            # Poll logs once more to confirm
            time.sleep(10)
            healed = _chaos_poll_logs(trace_id)

        if healed:
            result["healed"] = True
            try:
                postgres.update_incident_status(trace_id, "resolved")
                neo4j_client.update_incident_status_graph(trace_id, "resolved")
            except Exception as exc:
                logger.warning("Failed to mark incident healed: %s", exc)

        action_details = {
            "fix_result":   fix_result,
            "health_check": health,
            "healed":       healed,
        }

        if action_row:
            try:
                postgres.complete_action(
                    str(action_row["id"]),
                    "completed" if healed else "failed",
                    action_details,
                )
            except Exception as exc:
                logger.warning("Could not complete runtime_fix action record: %s", exc)

        result["actions"].append({
            "type":    "runtime_fix",
            "details": action_details,
        })
        logger.info(
            "Runtime fix for trace_id=%s: healed=%s", trace_id, healed
        )

    logger.info(
        "Remediation plan for trace_id=%s: actions=%s wants_pr=%s",
        trace_id,
        actions_triggered,
        wants_pr,
    )
    return result
