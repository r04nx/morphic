"""
RCA Agent — Layer 2 (Intelligence Layer)
Calls Anthropic Claude to produce a strict JSON RCA document.

Enhancement: Before calling Claude, fetches the actual Java source files
from https://github.com/Sparky17561/HackathonPS so Claude can reference
specific line numbers in its fix suggestion.

After RCA, updates PostgreSQL and Neo4j with the result.
"""

import json
import logging
import re
from typing import Any

import anthropic

from config import Config
from db import postgres, neo4j_client
from utils.github_source import fetch_sources_for_incident

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

Your job is to analyze structured log data AND the actual Java source code to produce a precise Root Cause Analysis (RCA).

CRITICAL RULES:
1. You MUST return ONLY a valid JSON object — no prose, no markdown, no code fences.
2. The JSON must strictly match the schema provided.
3. The suggested_fix.target_class MUST be the exact Java class name from the source code provided.
4. suggested_fix.patch MUST be real, compilable Java code based on the ACTUAL source provided.
5. suggested_fix.patch MUST reference specific line numbers from the source (e.g. "// Fix at line 42").
6. suggested_fix.rationale MUST explain which lines are problematic and why.
7. blast_radius must be exactly one of: LOW, MEDIUM, HIGH, CRITICAL
8. confidence_score must be a float between 0.0 and 1.0
   - Use 0.9+ when you can see the exact buggy line in the source
   - Use 0.7-0.89 when the bug is strongly implied by the source
   - Use 0.5-0.69 when source partially confirms the log signals
   - Use below 0.5 when source is not available or doesn't match
9. github_pr.labels must be a JSON array of strings.

The five incident scenarios you must recognize and prioritize:
- Gateway Timeout → Duplicate Payment (idempotency failure — look for missing idempotency key checks)
- Partial Write → Orphaned Payment Record (transaction rollback missing — look for @Transactional gaps)
- Race Condition → Negative Stock (missing synchronization — look for unsynchronized inventory updates)
- Async Trace Loss → MDC Propagation Failure (ThreadLocal not propagated — look for async executor config)
- Inconsistent Order State → Stuck CREATED (missing state machine guard — look for order status transitions)

When source code is provided:
- Read it carefully and find the EXACT lines responsible for the bug
- Quote the problematic code in your rationale
- Write the patch as a targeted fix to those exact lines
- Include the line numbers in comments within the patch
"""

_RCA_SCHEMA = """{
  "classification": "string",
  "root_cause": "string (one sentence, referencing the specific Java class and line)",
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
    "target_class": "string (exact class name from source)",
    "patch": "string (compilable Java code with line number comments)",
    "rationale": "string (explain which lines are buggy and why)",
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
# Prompt builder
# ---------------------------------------------------------------------------

def _format_source_block(src: dict) -> str:
    """Format a single fetched source file for the prompt."""
    return (
        f"=== SOURCE: {src['class_name']} ===\n"
        f"File: {src['file_path']}\n"
        f"GitHub: {src['github_url']}\n"
        f"Lines: {src['line_count']}\n"
        f"\n"
        f"{src['numbered_src']}\n"
    )


def _build_user_prompt(
    incident: dict[str, Any],
    log_slice: list[dict[str, Any]],
    source_files: list[dict],
) -> str:
    """Compose a precise prompt containing logs + actual Java source."""
    log_text = json.dumps(log_slice, indent=2, default=str)[:6000]  # cap log tokens

    # Build source section (cap each file at 300 lines to stay within context)
    source_section = ""
    if source_files:
        source_parts = []
        for src in source_files:
            lines = src["numbered_src"].splitlines()
            if len(lines) > 300:
                # Include first 50 + last 50 + middle section most likely to contain bug
                trimmed = (
                    lines[:50]
                    + [f"  ... ({len(lines) - 100} lines omitted) ..."]
                    + lines[-50:]
                )
                src_text = "\n".join(trimmed)
            else:
                src_text = src["numbered_src"]

            source_parts.append(
                f"=== SOURCE: {src['class_name']} ===\n"
                f"File: {src['file_path']}\n"
                f"GitHub: {src['github_url']}\n"
                f"Total lines: {src['line_count']}\n\n"
                f"{src_text}\n"
            )
        source_section = (
            "\n=== JAVA SOURCE CODE (actual repo — reference line numbers in your fix) ===\n"
            + "\n".join(source_parts)
        )
    else:
        source_section = "\n=== JAVA SOURCE CODE ===\n(Not available — use log signals only)\n"

    return f"""Analyze the following incident using the log data AND the actual Java source code.
Reference specific line numbers in your fix.

=== INCIDENT METADATA ===
trace_id:       {incident.get("trace_id")}
timestamp:      {incident.get("timestamp")}
service:        {incident.get("service")}
classification: {incident.get("triage_classification", "unknown")}
blast_radius:   {incident.get("triage_blast_radius", "unknown")}
async_orphan:   {incident.get("async_orphan", False)}

=== LOG SLICE (this trace_id only) ===
{log_text}
{source_section}
=== REQUIRED JSON SCHEMA ===
{_RCA_SCHEMA}

IMPORTANT:
- Your suggested_fix.patch must be based on the ACTUAL source code shown above.
- Reference line numbers like: "// Line 87: missing @Transactional — add it here"
- Set confidence_score >= 0.85 if you can see the exact buggy line.

Return ONLY the JSON object. No other text."""


# ---------------------------------------------------------------------------
# JSON extractor
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first valid JSON object from Claude's response."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
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
    Call Claude for a single incident with real Java source context.

    Steps:
    1. Fetch log slice from PostgreSQL
    2. Identify relevant Java classes from log signals
    3. Fetch actual source files from GitHub (Sparky17561/HackathonPS)
    4. Build Claude prompt with logs + numbered source
    5. Parse and validate Claude's JSON response
    6. Persist to PostgreSQL + Neo4j

    Args:
        incident: normalised incident dict from the ingestion/triage pipeline.

    Returns:
        Full RCA dict on success, None on failure.
    """
    trace_id    = incident.get("trace_id", "unknown")
    incident_id = incident.get("incident_id")

    # -----------------------------------------------------------------------
    # Step 1: Fetch log slice from PostgreSQL
    # -----------------------------------------------------------------------
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

    # Fall back to the raw incident fields
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

    # -----------------------------------------------------------------------
    # Step 2 + 3: Fetch real Java source from GitHub
    # -----------------------------------------------------------------------
    source_files: list[dict] = []
    try:
        source_files = fetch_sources_for_incident(
            log_slice=log_slice,
            triage_classification=incident.get("triage_classification", ""),
            max_files=2,          # keep context focused
        )
        if source_files:
            logger.info(
                "RCA GitHub source context: %s",
                [s["class_name"] for s in source_files],
            )
        else:
            logger.info("No GitHub source files resolved for trace_id=%s — using log-only context", trace_id)
    except Exception as exc:
        logger.warning("GitHub source fetch failed for trace_id=%s: %s", trace_id, exc)

    # -----------------------------------------------------------------------
    # Step 4: Build prompt and call Claude
    # -----------------------------------------------------------------------
    user_prompt = _build_user_prompt(incident, log_slice, source_files)

    # Increase max_tokens when we have source code (larger response needed)
    max_tokens = 3072 if source_files else 2048

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

    # -----------------------------------------------------------------------
    # Step 5: Parse and validate
    # -----------------------------------------------------------------------
    try:
        rca = _extract_json(raw_text)
    except ValueError as exc:
        logger.error("RCA JSON parse failed for trace_id=%s: %s", trace_id, exc)
        return None

    # Enforce required fields / defaults
    rca.setdefault("trace_id",        trace_id)
    rca.setdefault("timestamp",       str(incident.get("timestamp", "")))
    rca.setdefault("confidence_score", 0.5)
    rca.setdefault("blast_radius",    incident.get("triage_blast_radius", "LOW"))
    rca.setdefault("classification",  incident.get("triage_classification", "Unknown"))
    rca.setdefault("log_signals",     {})
    rca.setdefault("suggested_fix",   {})
    rca.setdefault("github_pr",       {})

    # Validate blast_radius
    if rca["blast_radius"] not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        rca["blast_radius"] = "MEDIUM"

    # Clamp confidence score
    try:
        rca["confidence_score"] = max(0.0, min(1.0, float(rca["confidence_score"])))
    except (TypeError, ValueError):
        rca["confidence_score"] = 0.5

    # Annotate which source files were used (useful for the dashboard)
    rca["_source_context"] = [
        {"class": s["class_name"], "path": s["file_path"], "url": s["github_url"], "lines": s["line_count"]}
        for s in source_files
    ]

    logger.info(
        "RCA complete: trace_id=%s class=%s blast=%s confidence=%.2f source_files=%s",
        trace_id,
        rca.get("classification"),
        rca.get("blast_radius"),
        rca.get("confidence_score"),
        [s["class_name"] for s in source_files],
    )

    # -----------------------------------------------------------------------
    # Step 6: Persist to PostgreSQL + Neo4j
    # -----------------------------------------------------------------------
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
                "summary":          rca.get("root_cause", "")[:500],
            })
        except Exception as exc:
            logger.error("Failed to persist RCA to PostgreSQL: %s", exc)

    try:
        neo4j_client.link_rca_to_incident(trace_id, rca)
        neo4j_client.update_incident_status_graph(trace_id, "investigating")
    except Exception as exc:
        logger.warning("Neo4j RCA update failed: %s", exc)

    return rca
