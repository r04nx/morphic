# Morphic Agents Specification

## Problem Statement
Morphic is an AI-driven self-healing incident assistant that continuously monitors logs, detects failures, performs Root Cause Analysis (RCA), and triggers automated corrective actions with minimal human intervention.

The core objective is to move beyond passive monitoring to a proactive system that understands what went wrong, explains impact in human-readable language, and executes remediation workflows.

## Target Stack (Authoritative)
- **Core Backend**: Flask (Python)
- **LLM Provider**: Anthropic Claude (latest available models configured via environment)
- **Automation Layer**: GitHub Actions (scheduled runs + CI + PR automation)
- **Frontend**: React dashboard (live incident feed + per-trace timeline + RCA cards)
- **Chaos Backend Under Test**: Spring Boot service emitting incidents via `/logs`

## Four-Layer Framework (End-to-End)
### Layer 1: Log Ingestion & Deduplication
- Poll the chaos backend `/logs` endpoint every **30 seconds**.
- Deduplicate events by the compound key:
  - `timestamp`
  - `trace_id`
- Track processed offsets (or last-seen watermark) to prevent redundant alerts.
- Detect and flag **ASYNC-ORPHAN** entries (logs that have lost async trace correlation / MDC context).

### Layer 2: AI Reasoning (Intelligence Layer)
- Use Claude to transform an incident payload into a **structured JSON RCA** that includes:
  - Error classification + one-sentence root cause
  - Blast radius (LOW, MEDIUM, HIGH, CRITICAL)
  - A **usable Java code fix** anchored to the class referenced in the logs
  - Confidence score

### Layer 3: Automated Actions
After RCA generation, trigger at least two automated workflows:
- **Email alert** with incident summary and severity
- **GitHub PR creation** via GitHub REST API using the AI-generated code fix

Optional actions (must be explicitly enabled):
- Service restart / rollback
- Ticket creation (e.g., Jira)

### Layer 4: Dashboard / UX
React frontend must provide:
- Live incident feed
- Timeline view per `trace_id`
- RCA cards understandable by non-engineers
- Action execution history (what ran, when, results)

## Target Incident Scenarios (Must Support)
Morphic prioritizes detection and remediation for the following bug types in the Spring Boot chaos backend:
1. Gateway Timeout resulting in duplicate payments
2. Partial Write leading to orphaned payment records
3. Race Condition causing negative stock levels
4. Async Trace Loss due to MDC propagation failures
5. Inconsistent Order State (orders stuck in CREATED)

## Agents (Roles and Responsibilities)
This file defines “agents” as logical components (not necessarily separate processes). They can be implemented as Flask services/modules, background workers, or GitHub Actions jobs.

### 1) Orchestrator Agent
- **Responsibility**: Coordinate the end-to-end pipeline from ingestion → RCA → actions → persistence.
- **Inputs**:
  - New log batch from `/logs`
  - Previously processed watermark/offset state
- **Outputs**:
  - Normalized incident objects
  - Scheduling decisions (which incidents warrant RCA)

### 2) Ingestion + Dedup Agent
- **Responsibility**: Poll, normalize, deduplicate, and store incident candidates.
- **Key invariants**:
  - Never emit the same `(timestamp, trace_id)` incident twice.
  - Persist the last processed watermark in durable storage.
- **ASYNC-ORPHAN detection**:
  - Flag events where async log lines lack expected trace correlation fields.

### 3) Triage Agent
- **Responsibility**: Classify and prioritize incidents before spending LLM tokens.
- **Rules**:
  - Suppress duplicates
  - Rate-limit similar incidents
  - Escalate severity for the 5 target scenarios
- **Output**:
  - “Needs RCA” decision with minimal metadata

### 4) RCA Agent (Claude)
- **Responsibility**: Produce an RCA JSON document and a code fix proposal.
- **Constraints**:
  - Must output valid JSON matching the schema below
  - Must reference the Java class mentioned by the logs (no guessing unrelated files)
  - Must include a confidence score and human-readable impact explanation
- **Token efficiency**:
  - Provide the smallest sufficient incident context
  - Include only the relevant log slice for the `trace_id`

### 5) Remediation Planner Agent
- **Responsibility**: Decide which actions to run based on `blast_radius`, `classification`, and `confidence_score`.
- **Examples**:
  - LOW confidence → alert only (no PR)
  - HIGH/CRITICAL + high confidence → alert + PR

### 6) GitHub PR Agent
- **Responsibility**: Apply the AI-suggested patch to the Java codebase and open a PR.
- **Hard requirements**:
  - Do not commit secrets
  - Run tests/linters relevant to the change before opening PR (locally or in CI)
  - Include `trace_id` and incident summary in PR body
- **Implementation note**:
  - Can run as a GitHub Action job that uses the GitHub REST API to create a branch + commit + PR.

### 7) Notification Agent (Email)
- **Responsibility**: Send human-readable summaries.
- **Minimum email content**:
  - Severity / blast radius
  - One-sentence root cause
  - `trace_id`
  - Link to the dashboard incident detail
  - Link to PR (if created)

### 8) UX/Dashboard Agent
- **Responsibility**: Present incidents, RCA, and action history.
- **Data**:
  - Reads from the incident store
  - Subscribes/polls for updates (implementation-dependent)

## RCA JSON Contract (Strict)
All RCA outputs must conform to the following JSON structure.

```json
{
  "classification": "string",
  "root_cause": "string",
  "blast_radius": "LOW|MEDIUM|HIGH|CRITICAL",
  "impact": "string",
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
    "patch": "string",
    "rationale": "string",
    "tests": ["string"]
  },
  "github_pr": {
    "title": "string",
    "body": "string",
    "labels": ["string"]
  },
  "confidence_score": 0.0
}
```

## Claude Configuration (Latest Models)
- Model selection must be **environment-driven** so the project can track Anthropic’s latest Claude models without code churn.
- Recommended environment variables:
  - `ANTHROPIC_API_KEY`
  - `ANTHROPIC_MODEL` (set to your chosen latest Claude model)

## Storage & State (Dedup + Timeline)
Morphic must persist:
- **Processed offsets / watermarks** for polling `/logs`
- **Incident store** keyed by `trace_id` with a timeline of events
- **RCA results** keyed by incident id
- **Action execution history** (action name, start/end time, status, output)

Implementation can be lightweight (SQLite) for demo, or durable (Postgres/Redis) for production.

## GitHub Actions Automation
GitHub Actions is the automation backbone and should cover:

### Scheduled Incident Polling
- A scheduled workflow runs every 30 seconds is not supported by GitHub cron; use:
  - 1-minute schedule for demo, or
  - a long-running worker outside GitHub Actions for true 30-second polling.

### CI Gatekeeping
- On PRs, run:
  - Backend unit tests (Flask)
  - Frontend checks (React)
  - Any Java checks relevant to applying fixes in the chaos backend repository (if present in the same repo)

### PR Creation Workflow
- A workflow job with permissions to:
  - create branches
  - push commits
  - open PRs
- Requires GitHub token configuration (use GitHub-provided token or a fine-scoped PAT when necessary).

## Operational Guidelines
### Always Do
- Deduplicate events before processing to avoid redundant alerts.
- Ensure every RCA includes a confidence score and a plain-English impact explanation.
- Anchor any suggested Java fix to the class referenced by the log.
- Prioritize the five core bug scenarios.

### Ask First
- Before performing destructive corrective actions (restart/rollback).
- Before adding heavy new dependencies across backend/frontend.

### Never Do
- Never commit secrets or API keys.
- Never re-alert on the same incident; processed offsets must be tracked.
- Do not guess API signatures; anchor changes in repository sources.

## PR Checklist (For Automated and Human PRs)
- [ ] RCA is explained in plain English.
- [ ] Automation triggers (Email/GitHub) are verified.
- [ ] Code fix addresses the specific `trace_id` failure.
- [ ] Alert noise has been filtered and deduplicated.
- [ ] Confidence score supports the chosen action (alert-only vs PR).
