"""
RCA Agent — Layer 2 (Intelligence Layer)
Calls Anthropic Claude to produce a strict JSON RCA document.

Before calling Claude:
  1. Fetches the log slice for this trace_id from PostgreSQL.
  2. Extracts the Java class name from the log entries.
  3. Downloads the actual Java source from GitHub (Sparky17561/HackathonPS).
  4. Injects both into the Claude prompt so Claude can reference exact line numbers.
  5. Falls back gracefully to log-only RCA if source fetch fails.

After RCA, persists the result to PostgreSQL and Neo4j.
"""

import json
import logging
import re
from typing import Any

import anthropic

from config import Config
from db import postgres, neo4j_client
from agents.github_source import fetch_java_source, extract_class_name_from_logs

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

Your job is to analyze structured log data and Java source code to produce a precise Root Cause Analysis (RCA).

CRITICAL RULES:
1. You MUST return ONLY a valid JSON object — no prose, no markdown, no code fences.
2. The JSON must strictly match the schema provided.
3. When source code is given, suggested_fix.target_class MUST be the exact Java class name from that source.
4. When source code is given, suggested_fix.patch MUST reference specific line numbers with comments like:
      // Line 91-103: shouldFail() triggers RuntimeException without idempotency check
5. suggested_fix.patch must be real, compilable Java — not pseudocode.
6. blast_radius must be exactly one of: LOW, MEDIUM, HIGH, CRITICAL
7. confidence_score rules:
   - 0.90–1.0  → exact buggy line visible in source
   - 0.70–0.89 → bug strongly implied by source structure
   - 0.50–0.69 → source partially confirms logs
   - below 0.5 → no source available, log-only analysis
8. github_pr.labels must be a JSON array of strings.

The five incident scenarios you must recognize:
- Gateway Timeout → Duplicate Payment      (no idempotency key — look for retry without dedup)
- Partial Write   → Orphaned Payment       (missing @Transactional — payment saved, order not updated)
- Race Condition  → Negative Stock         (unsynchronized inventory decrement)
- Async Trace Loss→ MDC Propagation Failure(ThreadLocal lost across async boundaries)
- Inconsistent Order State → Stuck CREATED (missing state machine transition guard)
"""

_RCA_SCHEMA = """{
  "classification": "string",
  "root_cause": "string (one sentence, naming the class and line if source was available)",
  "blast_radius": "LOW|MEDIUM|HIGH|CRITICAL",
  "impact": "string (plain English, non-technical description)",
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
    "patch": "string (compilable Java with // Line N: comments)",
    "rationale": "string (quote the problematic lines and explain why they are wrong)",
    "tests": ["string"]
  },
  "github_pr": {
    "title": "string",
    "body": "string",
    "labels": ["string"]
  },
  "confidence_score": 0.0
}"""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_user_prompt(
    incident: dict[str, Any],
    log_slice: list[dict[str, Any]],
    class_name: str | None,
    source: dict | None,
) -> str:
    """
    Build the Claude user prompt.
    Follows the exact structure the user specified:

        Here are the relevant logs:
        {log_slice}

        Here is the actual Java source code for {class_name}:
        {source_code}

        Analyze both the logs AND the source code ...
    """
    log_text = json.dumps(log_slice, indent=2, default=str)[:6000]

    # --- Source section ---
    if source:
        # Cap at 300 lines to stay within context window while keeping all key sections
        lines = source["numbered_src"].splitlines()
        if len(lines) > 300:
            trimmed = (
                lines[:80]
                + [f"", f"    ... ({len(lines) - 160} lines omitted for brevity) ...", ""]
                + lines[-80:]
            )
            src_text = "\n".join(trimmed)
        else:
            src_text = source["numbered_src"]

        source_section = (
            f"Here is the actual Java source code for {source['class_name']}:\n"
            f"(File: {source['file_path']} | {source['github_url']})\n\n"
            f"{src_text}"
        )
        analysis_instruction = (
            "Analyze both the logs AND the source code to provide surgical RCA with exact line numbers.\n"
            "Quote the specific lines that are buggy in your rationale.\n"
            "Your patch must fix those exact lines — include '// Line N:' comments to identify them."
        )
    else:
        source_section = (
            f"Java source code for {class_name or 'the affected class'} "
            f"could not be retrieved — perform log-only analysis."
        )
        analysis_instruction = (
            "Analyze the logs to determine the root cause.\n"
            "Set confidence_score below 0.5 since no source code is available."
        )

    return f"""=== INCIDENT METADATA ===
trace_id:       {incident.get("trace_id")}
timestamp:      {incident.get("timestamp")}
service:        {incident.get("service")}
classification: {incident.get("triage_classification", "unknown")}
blast_radius:   {incident.get("triage_blast_radius", "unknown")}
async_orphan:   {incident.get("async_orphan", False)}

Here are the relevant logs:
{log_text}

{source_section}

{analysis_instruction}

=== REQUIRED JSON SCHEMA ===
{_RCA_SCHEMA}

Return ONLY the JSON object. No other text."""


# ---------------------------------------------------------------------------
# JSON extractor
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from Claude's response."""
    # Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Claude returned non-JSON response: {text[:300]}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_rca(incident: dict[str, Any]) -> dict[str, Any] | None:
    """
    Run the full RCA pipeline for a single incident.

    Steps:
      1. Fetch log slice from PostgreSQL (fallback: raw incident fields).
      2. Extract Java class name from the log entries.
      3. Fetch actual Java source from GitHub (raw URL → REST API fallback).
      4. Build Claude prompt with logs + source code (or log-only if fetch fails).
      5. Call Claude, parse and validate the JSON response.
      6. Persist RCA to PostgreSQL and Neo4j.

    Returns the full RCA dict on success, None on failure.
    """
    trace_id    = incident.get("trace_id", "unknown")
    incident_id = incident.get("incident_id")

    # ------------------------------------------------------------------
    # Step 1: Fetch log slice
    # ------------------------------------------------------------------
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

    # Fallback to raw incident fields if DB returned nothing
    if not log_slice:
        log_slice = [
            {
                "timestamp": str(incident.get("timestamp")),
                "level":     incident.get("level"),
                "service":   incident.get("service"),
                "endpoint":  incident.get("endpoint"),
                "message":   incident.get("message"),
                "exception": incident.get("exception"),
                "class":     incident.get("class"),
            }
        ]

    # ------------------------------------------------------------------
    # Step 2: Extract Java class name from logs
    # ------------------------------------------------------------------
    class_name: str | None = extract_class_name_from_logs(log_slice)

    # Heuristic fallback based on triage classification
    if not class_name:
        classification = (incident.get("triage_classification") or "").lower()
        if "payment" in classification:
            class_name = "PaymentService"
        elif "order" in classification or "stuck" in classification:
            class_name = "OrderService"
        elif "stock" in classification or "inventory" in classification:
            class_name = "InventoryService"
        elif "async" in classification or "mdc" in classification or "trace" in classification:
            class_name = "AsyncConfig"
        else:
            class_name = None

    logger.info("RCA class target for trace_id=%s: %s", trace_id, class_name or "(none)")

    # ------------------------------------------------------------------
    # Step 3: Fetch Java source from GitHub
    # ------------------------------------------------------------------
    source: dict | None = None
    if class_name:
        try:
            source = fetch_java_source(class_name)
            if source:
                logger.info(
                    "GitHub source loaded: %s (%d lines) for trace_id=%s",
                    source["class_name"], source["line_count"], trace_id,
                )
            else:
                logger.info(
                    "GitHub source not available for %s — proceeding with log-only RCA",
                    class_name,
                )
        except Exception as exc:
            logger.warning(
                "GitHub source fetch error for %s (trace_id=%s): %s — falling back to log-only",
                class_name, trace_id, exc,
            )

    # ------------------------------------------------------------------
    # Step 4: Build prompt and call Claude
    # ------------------------------------------------------------------
    user_prompt = _build_user_prompt(incident, log_slice, class_name, source)
    max_tokens  = 3072 if source else 2048

    logger.info(
        "Calling Claude model=%s max_tokens=%d source=%s trace_id=%s",
        Config.ANTHROPIC_MODEL, max_tokens, bool(source), trace_id,
    )

    try:
        response = _get_client().messages.create(
            model=Config.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
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

    # ------------------------------------------------------------------
    # Step 5: Parse and validate
    # ------------------------------------------------------------------
    try:
        rca = _extract_json(raw_text)
    except ValueError as exc:
        logger.error("RCA JSON parse failed for trace_id=%s: %s", trace_id, exc)
        return None

    # Enforce required fields with safe defaults
    rca.setdefault("trace_id",         trace_id)
    rca.setdefault("timestamp",        str(incident.get("timestamp", "")))
    rca.setdefault("confidence_score", 0.5)
    rca.setdefault("blast_radius",     incident.get("triage_blast_radius", "LOW"))
    rca.setdefault("classification",   incident.get("triage_classification", "Unknown"))
    rca.setdefault("log_signals",      {})
    rca.setdefault("suggested_fix",    {})
    rca.setdefault("github_pr",        {})

    # Validate blast_radius
    if rca["blast_radius"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        rca["blast_radius"] = "MEDIUM"

    # Clamp confidence score to [0.0, 1.0]
    try:
        rca["confidence_score"] = max(0.0, min(1.0, float(rca["confidence_score"])))
    except (TypeError, ValueError):
        rca["confidence_score"] = 0.5

    # Attach source context metadata so the dashboard can show which file was used
    rca["_source_context"] = {
        "class_name":  source["class_name"]  if source else None,
        "file_path":   source["file_path"]   if source else None,
        "github_url":  source["github_url"]  if source else None,
        "line_count":  source["line_count"]  if source else None,
        "source_used": source is not None,
    }

    logger.info(
        "RCA complete — trace_id=%s classification=%s blast=%s confidence=%.2f source_used=%s",
        trace_id,
        rca.get("classification"),
        rca.get("blast_radius"),
        rca.get("confidence_score"),
        source is not None,
    )

    # ------------------------------------------------------------------
    # Step 6: Persist to PostgreSQL + Neo4j
    # ------------------------------------------------------------------
    if incident_id:
        try:
            postgres.upsert_incident({
                "trace_id":         trace_id,
                "timestamp":        incident.get("timestamp"),
                "service":          incident.get("service"),
                "classification":   rca.get("classification"),
                "root_cause":       rca.get("root_cause"),
                "blast_radius":     rca.get("blast_radius"),
                "impact":           rca.get("impact"),
                "confidence_score": rca.get("confidence_score"),
                "status":           "investigating",
                "rca_json":         rca,
                "summary":          (rca.get("root_cause") or "")[:500],
            })
        except Exception as exc:
            logger.error("Failed to persist RCA to PostgreSQL for trace_id=%s: %s", trace_id, exc)

    try:
        neo4j_client.link_rca_to_incident(trace_id, rca)
        neo4j_client.update_incident_status_graph(trace_id, "investigating")
    except Exception as exc:
        logger.warning("Neo4j RCA update failed for trace_id=%s: %s", trace_id, exc)

    return rca
