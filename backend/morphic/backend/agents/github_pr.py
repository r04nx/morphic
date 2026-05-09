"""
GitHub PR Agent — Layer 3 (Action)
Uses the GitHub REST API to:
  1. Get the default branch SHA
  2. Create a feature branch
  3. Commit Claude's suggested patch to the target Java file
  4. Open a Pull Request with trace_id + RCA summary in the body
"""

import base64
import logging
from typing import Any

import requests

from config import Config
from db import postgres

logger = logging.getLogger(__name__)

_GITHUB_API = Config.GITHUB_API_BASE


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {Config.GITHUB_TOKEN}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _api(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{_GITHUB_API}{path}"
    resp = requests.request(method, url, headers=_headers(), timeout=20, **kwargs)
    return resp


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _get_default_branch_sha(repo: str) -> tuple[str, str]:
    """Return (branch_name, sha) for the repo's default branch."""
    resp = _api("GET", f"/repos/{repo}")
    resp.raise_for_status()
    default_branch = resp.json()["default_branch"]

    resp2 = _api("GET", f"/repos/{repo}/git/ref/heads/{default_branch}")
    resp2.raise_for_status()
    sha = resp2.json()["object"]["sha"]
    return default_branch, sha


def _create_branch(repo: str, branch_name: str, sha: str) -> None:
    payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
    resp = _api("POST", f"/repos/{repo}/git/refs", json=payload)
    if resp.status_code == 422:
        logger.info("Branch %s already exists — reusing", branch_name)
    else:
        resp.raise_for_status()


def _get_file_sha(repo: str, path: str, branch: str) -> str | None:
    """Return the existing blob SHA for a file, or None if it doesn't exist."""
    resp = _api("GET", f"/repos/{repo}/contents/{path}", params={"ref": branch})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json().get("sha")


def _commit_file(
    repo: str,
    branch: str,
    file_path: str,
    content: str,
    commit_message: str,
    existing_sha: str | None,
) -> dict[str, Any]:
    encoded = base64.b64encode(content.encode()).decode()
    payload: dict[str, Any] = {
        "message": commit_message,
        "content": encoded,
        "branch":  branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha
    resp = _api("PUT", f"/repos/{repo}/contents/{file_path}", json=payload)
    resp.raise_for_status()
    return resp.json()


def _open_pr(
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    labels: list[str],
) -> dict[str, Any]:
    payload = {
        "title": title,
        "body":  body,
        "head":  head_branch,
        "base":  base_branch,
    }
    resp = _api("POST", f"/repos/{repo}/pulls", json=payload)
    resp.raise_for_status()
    pr = resp.json()
    pr_number = pr["number"]

    # Apply labels if the repo has them
    if labels:
        try:
            _api(
                "POST",
                f"/repos/{repo}/issues/{pr_number}/labels",
                json={"labels": labels},
            )
        except Exception as exc:
            logger.warning("Failed to apply labels to PR #%d: %s", pr_number, exc)

    return pr


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def create_pr(
    incident: dict[str, Any],
    rca: dict[str, Any],
    incident_id: str | None = None,
    dashboard_url: str = "",
) -> dict[str, Any]:
    """
    Create a GitHub PR with Claude's suggested patch.

    Returns a dict with keys: pr_url, pr_number, branch, success, error.
    """
    repo = Config.GITHUB_REPO
    if not repo:
        return {"success": False, "error": "GITHUB_REPO not configured"}
    if not Config.GITHUB_TOKEN:
        return {"success": False, "error": "GITHUB_TOKEN not configured"}

    trace_id = rca.get("trace_id") or incident.get("trace_id", "unknown")
    suggested_fix = rca.get("suggested_fix", {})
    github_pr_meta = rca.get("github_pr", {})

    target_class: str = suggested_fix.get("target_class", "UnknownClass")
    patch: str = suggested_fix.get("patch", "// No patch generated")

    # Derive a sensible file path from the class name
    # e.g.  com.example.PaymentService → src/main/java/com/example/PaymentService.java
    java_file_path = _class_to_path(target_class)

    branch_name = f"morphic/fix-{trace_id[:16].replace(':', '-').replace('.', '-')}"
    pr_title = github_pr_meta.get("title") or f"fix: {rca.get('classification', 'incident')} [{trace_id[:8]}]"
    pr_body = _build_pr_body(trace_id, rca, dashboard_url, github_pr_meta)
    labels: list[str] = github_pr_meta.get("labels", ["morphic-auto", "incident-fix"])

    try:
        default_branch, sha = _get_default_branch_sha(repo)
    except Exception as exc:
        return {"success": False, "error": f"Cannot read repo default branch: {exc}"}

    try:
        _create_branch(repo, branch_name, sha)
    except Exception as exc:
        return {"success": False, "error": f"Branch creation failed: {exc}"}

    existing_sha = _get_file_sha(repo, java_file_path, branch_name)
    commit_message = (
        f"fix({target_class}): auto-remediation for trace {trace_id[:16]}\n\n"
        f"Generated by Morphic RCA agent.\n"
        f"Classification: {rca.get('classification')}\n"
        f"Blast radius: {rca.get('blast_radius')}\n"
        f"Confidence: {rca.get('confidence_score')}"
    )

    try:
        _commit_file(
            repo,
            branch_name,
            java_file_path,
            patch,
            commit_message,
            existing_sha,
        )
    except Exception as exc:
        return {"success": False, "error": f"File commit failed: {exc}"}

    try:
        pr = _open_pr(repo, pr_title, pr_body, branch_name, default_branch, labels)
    except Exception as exc:
        return {"success": False, "error": f"PR creation failed: {exc}"}

    pr_url = pr.get("html_url", "")
    pr_number = pr.get("number")
    logger.info("PR created: #%s %s for trace_id=%s", pr_number, pr_url, trace_id)

    # Record action in DB
    if incident_id:
        try:
            action_row = postgres.insert_action({
                "incident_id": incident_id,
                "action_type": "github_pr",
                "status":      "running",
                "details":     {"pr_url": pr_url, "pr_number": pr_number, "branch": branch_name},
            })
            postgres.complete_action(
                str(action_row["id"]),
                "completed",
                {"pr_url": pr_url, "pr_number": pr_number, "branch": branch_name},
            )
        except Exception as exc:
            logger.warning("Failed to record github_pr action: %s", exc)

    return {
        "success":   True,
        "pr_url":    pr_url,
        "pr_number": pr_number,
        "branch":    branch_name,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _class_to_path(class_name: str) -> str:
    """
    Convert a Java fully-qualified class name to a relative file path.
    'com.example.service.PaymentService' → 'src/main/java/com/example/service/PaymentService.java'
    If the name has no dots it is treated as a simple class in the root source dir.
    """
    if "." in class_name:
        return "src/main/java/" + class_name.replace(".", "/") + ".java"
    return f"src/main/java/{class_name}.java"


def _build_pr_body(
    trace_id: str,
    rca: dict[str, Any],
    dashboard_url: str,
    meta: dict[str, Any],
) -> str:
    fix = rca.get("suggested_fix", {})
    signals = rca.get("log_signals", {})
    incident_link = f"{dashboard_url}/incidents?trace={trace_id}" if dashboard_url else ""

    custom_body = meta.get("body", "")

    return f"""## 🤖 Morphic Auto-Remediation PR

**Trace ID:** `{trace_id}`
**Classification:** {rca.get("classification", "unknown")}
**Blast Radius:** {rca.get("blast_radius", "unknown")}
**Confidence Score:** {rca.get("confidence_score", 0.0):.0%}

---

### Root Cause
{rca.get("root_cause", "Not determined")}

### Impact
{rca.get("impact", "Not determined")}

### Log Signals
| Field | Value |
|-------|-------|
| Service | `{signals.get("service", "unknown")}` |
| Endpoint | `{signals.get("endpoint", "")}` |
| Exception | `{signals.get("exception_class", "")}` |
| Error | {signals.get("error_message", "")[:200]} |

### Suggested Fix — `{fix.get("target_class", "")}`
**Rationale:** {fix.get("rationale", "")}

### Suggested Tests
{chr(10).join(f"- `{t}`" for t in fix.get("tests", [])) or "- No tests specified"}

---

{f'📊 [View Incident on Dashboard]({incident_link})' if incident_link else ""}

{custom_body}

---
*This PR was automatically generated by [Morphic](https://github.com) in response to a production incident.*
*Do NOT merge without human review.*
"""
