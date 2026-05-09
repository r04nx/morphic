Project Vision
Morphic is a self-healing system designed to continuously monitor logs, detect anomalies, perform Root Cause Analysis (RCA), and trigger corrective actions with minimal human intervention. It acts as a smart AI teammate that cuts through alert noise to highlight and fix critical issues.
The Stack

    Intelligence: Anthropic Claude API (Claude 3.5 Sonnet) for the reasoning layer.
    Backend: Flask / Spring Boot chaos backend.
    Frontend: React dashboard for live incident feeds and RCA cards.
    Automation: n8n, GitHub REST API (for PRs), and Webhooks.

Core Architecture (4-Layer Framework)

    Layer 1 (Ingestion): Poll /logs every 30s, deduplicate by timestamp + trace_id, and flag ASYNC-ORPHAN entries.
    Layer 2 (Reasoning): Call Claude to produce a structured JSON RCA including classification, root cause, blast radius, and a Java code fix.
    Layer 3 (Actions): Automate at least two actions: (a) Email alerts and (b) GitHub PR creation via REST API.
    Layer 4 (UX): A React frontend rshowing a timeline view per trace_id and action history.

Operational Guidelines
✅ Always Do

    Deduplicate events before processing to avoid redundant alerts.
    Ensure every RCA includes a confidence score and a clear impact explanation in human language.
    Run tsc --noEmit or equivalent type-checks after generating code fixes to prevent hallucinations.
    Focus on the five core bugs: Gateway Timeout, Partial Write, Race Condition, Async Trace Loss, and Inconsistent Order State.

⚠ Ask First

    Before performing a simulated "service restart" or destructive corrective action.
    Before adding new heavy dependencies to the Java or React projects.

🚫 Never Do

    Never commit secrets or API keys to the repository.
    Never re-alert on the same incident; track processed offsets meticulously.
    Do not guess at API signatures; reference src/ files directly to anchor code generation in reality.

Commands

    Build/Test: mvn clean install (Backend) | npm run build (Frontend).
    Verify Fix: pytest -v or relevant unit test commands for specific Java classes.
    Log Access: Poll the /logs endpoint for the structured incident payload.

RCA Output Format
When generating RCA, Claude must return a structured JSON object:

{
  "classification": "Error Category",
  "root_cause": "One sentence explanation",
  "blast_radius": "LOW/MEDIUM/HIGH/CRITICAL",
  "suggested_fix": "Code snippet for Java class",
  "github_pr_desc": "Detailed PR description",
  "confidence_score": 0.95
}


PR Checklist

    [ ] RCA is explained in plain English.
    [ ] Automation triggers (Email/GitHub) are verified.
    [ ] Code fix addresses the specific trace_id failure.
    [ ] Alert noise has been filtered and deduplicated.