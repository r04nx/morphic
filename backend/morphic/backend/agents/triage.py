"""
Triage Agent — Layer 1.5
Classifies and prioritises incidents before spending LLM tokens.
Suppresses duplicates and rate-limits repeated alert classes.
"""

import logging
import re
from typing import Any

from db import redis_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity escalation rules for the 5 core bug scenarios
# ---------------------------------------------------------------------------

_RULES: list[dict[str, Any]] = [
    {
        "name": "Gateway Timeout → Duplicate Payment",
        "patterns": [
            r"gateway.{0,20}timeout",
            r"duplicate.{0,20}payment",
            r"GATEWAY_TIMEOUT",
            r"idempotency",
        ],
        "blast_radius": "HIGH",
        "priority": 1,
    },
    {
        "name": "Partial Write → Orphaned Payment",
        "patterns": [
            r"partial.{0,20}write",
            r"orphan.{0,20}payment",
            r"payment.{0,20}orphan",
            r"PARTIAL_WRITE",
            r"partial commit",
        ],
        "blast_radius": "HIGH",
        "priority": 2,
    },
    {
        "name": "Race Condition → Negative Stock",
        "patterns": [
            r"race.{0,20}condition",
            r"negative.{0,20}stock",
            r"stock.{0,20}negative",
            r"inventory.{0,20}negative",
            r"RACE_CONDITION",
            r"optimistic lock",
        ],
        "blast_radius": "CRITICAL",
        "priority": 1,
    },
    {
        "name": "Async Trace Loss → MDC Failure",
        "patterns": [
            r"async.{0,20}(trace|context|mdc)",
            r"mdc.{0,20}(loss|missing|null|propagat)",
            r"ASYNC.ORPHAN",
            r"trace.{0,20}loss",
            r"missing.{0,20}trace",
        ],
        "blast_radius": "MEDIUM",
        "priority": 3,
    },
    {
        "name": "Inconsistent Order State → Stuck CREATED",
        "patterns": [
            r"stuck.{0,20}created",
            r"order.{0,20}stuck",
            r"state.{0,20}inconsist",
            r"INCONSISTENT_STATE",
            r"order.*status.*CREATED",
        ],
        "blast_radius": "MEDIUM",
        "priority": 2,
    },
]

# Incidents with these log levels are always considered for RCA
_HIGH_SEVERITY_LEVELS = {"ERROR", "FATAL", "CRITICAL"}

# Minimum threshold: only ERROR/FATAL or known pattern → triage
_DEFAULT_BLAST_RADIUS = "LOW"


def _match_rules(text: str) -> dict[str, Any] | None:
    """Return the first matching rule dict or None."""
    text_lower = text.lower()
    for rule in sorted(_RULES, key=lambda r: r["priority"]):
        for pattern in rule["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return rule
    return None


def classify(incident: dict[str, Any]) -> dict[str, Any]:
    """
    Examine an incident and return a triage decision:
    {
        "needs_rca": bool,
        "blast_radius": "LOW|MEDIUM|HIGH|CRITICAL",
        "classification": str,
        "suppressed": bool,
        "suppression_reason": str | None,
    }
    """
    trace_id = incident.get("trace_id", "")
    level = (incident.get("level") or "").upper()
    message = incident.get("message") or ""
    exception = incident.get("exception") or ""
    combined_text = f"{message} {exception}"

    # --- 1. Check for matching core rule ---
    matched_rule = _match_rules(combined_text)

    blast_radius = matched_rule["blast_radius"] if matched_rule else _DEFAULT_BLAST_RADIUS
    classification = matched_rule["name"] if matched_rule else _infer_classification(level, exception)

    # --- 2. Only ERROR/FATAL or matched rules qualify for RCA ---
    needs_rca = bool(matched_rule) or level in _HIGH_SEVERITY_LEVELS

    # --- 3. Rate-limit: suppress if too many of the same class recently ---
    suppressed = False
    suppression_reason: str | None = None

    if needs_rca:
        try:
            if redis_client.is_rate_limited(classification):
                suppressed = True
                suppression_reason = f"Rate-limited: too many '{classification}' alerts in the last 5 minutes"
                needs_rca = False
                logger.info(
                    "Suppressed triage for trace_id=%s reason=%s",
                    trace_id,
                    suppression_reason,
                )
            else:
                redis_client.increment_rate_counter(classification)
        except Exception as exc:
            logger.warning("Rate-limit check failed (fail-open): %s", exc)

    # --- 4. Flag ASYNC-ORPHAN separately ---
    if incident.get("async_orphan"):
        if not matched_rule:
            classification = "Async Trace Loss → MDC Failure"
            blast_radius = "MEDIUM"
            needs_rca = True

    result = {
        "needs_rca":          needs_rca,
        "blast_radius":       blast_radius,
        "classification":     classification,
        "suppressed":         suppressed,
        "suppression_reason": suppression_reason,
    }
    logger.info(
        "Triage result: trace_id=%s class=%s blast=%s needs_rca=%s suppressed=%s",
        trace_id,
        classification,
        blast_radius,
        needs_rca,
        suppressed,
    )
    return result


def _infer_classification(level: str, exception: str) -> str:
    if exception:
        # Use the simple class name
        parts = exception.strip().split(".")
        return parts[-1] if parts else exception
    if level in _HIGH_SEVERITY_LEVELS:
        return "Runtime Error"
    return "Informational"
