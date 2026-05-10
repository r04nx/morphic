"""
GitHub PR Agent — Layer 3 (Action)
Uses PyGithub to:
  1. Get the default branch SHA
  2. Create a feature branch  (morphic/fix-<trace_id>)
  3. Search the repo for the target Java class and commit Claude's patch
  4. Open a Pull Request with the full RCA in the body

Never raises exceptions — all errors are logged as warnings and the function
returns a result dict with success=False.
"""

import logging
import os
import re
from typing import Any

from config import Config
from db import postgres

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: find matching Java file in repo
# ---------------------------------------------------------------------------

def find_java_file(repo: Any, class_name: str) -> Any | None:
    """
    Search the repo tree for a .java file matching class_name.
    Tries both fully-qualified (com/example/Foo.java) and simple name (Foo.java).
    Returns a github.ContentFile or None.
    """
    # Simple class name (last segment after last dot)
    simple = class_name.split(".")[-1] if "." in class_name else class_name
    fq_path = "src/main/java/" + class_name.replace(".", "/") + ".java"

    # 1. Try the fully-qualified path directly
    try:
        return repo.get_contents(fq_path)
    except Exception:
        pass

    # 2. Walk the git tree and match by filename
    try:
        tree = repo.get_git_tree(repo.default_branch, recursive=True)
        for element in tree.tree:
            if element.type == "blob" and element.path.endswith(f"{simple}.java"):
                return repo.get_contents(element.path)
    except Exception as exc:
        logger.debug("Tree walk failed: %s", exc)

    return None


# ---------------------------------------------------------------------------
# Helper: apply patch to file content
# ---------------------------------------------------------------------------

def apply_patch(original: str, patch: str) -> str:
    """
    Apply Claude's suggested patch to the original file content.

    Strategy (in order):
      1. If patch is a unified diff (starts with @@), apply it line-by-line.
      2. If patch looks like a complete file replacement (contains 'class '),
         return the patch directly.
      3. Otherwise append the patch as a comment block so the file is still valid.
    """
    if not patch:
        return original

    patch = patch.strip()

    # Complete file replacement heuristic
    if re.search(r'\bclass\s+\w+', patch) and len(patch) > 200:
        logger.debug("apply_patch: treating patch as full file replacement")
        return patch

    # Unified diff heuristic
    if patch.startswith("@@") or patch.startswith("---"):
        try:
            return _apply_unified_diff(original, patch)
        except Exception as exc:
            logger.debug("Unified diff failed (%s), appending as comment block", exc)

    # Fallback: append as a comment so the file at least compiles
    return original + f"\n\n/* ===== Morphic AI suggested patch =====\n{patch}\n===== end patch ===== */\n"


def _apply_unified_diff(original: str, patch: str) -> str:
    """
    Minimal unified diff application (handles @@ hunks).
    Not a full GNU patch — good enough for Claude's typical output.
    """
    orig_lines = original.splitlines(keepends=True)
    result = list(orig_lines)
    offset = 0

    for hunk in re.split(r'(?=^@@)', patch, flags=re.MULTILINE):
        header = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', hunk)
        if not header:
            continue
        old_start = int(header.group(1)) - 1   # 0-indexed
        new_lines: list[str] = []
        hunk_lines = hunk.splitlines(keepends=True)[1:]   # skip @@ line

        for line in hunk_lines:
            if line.startswith("+"):
                new_lines.append(line[1:])
            elif line.startswith("-"):
                pass  # remove
            else:
                new_lines.append(line[1:] if line.startswith(" ") else line)

        old_count = int(header.group(2) or 1)
        insert_at = old_start + offset
        result[insert_at: insert_at + old_count] = new_lines
        offset += len(new_lines) - old_count

    return "".join(result)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def raise_pr(rca_result: dict[str, Any]) -> str | None:
    """
    Simplified entry point called by the orchestrator.

    Returns the PR html_url on success, or None on failure/skip.
    """
    result = create_pr(
        incident=rca_result,
        rca=rca_result,
        incident_id=rca_result.get("incident_id"),
        dashboard_url=Config.DASHBOARD_URL,
    )
    return result.get("pr_url") if result.get("success") else None


def create_pr(
    incident: dict[str, Any],
    rca: dict[str, Any],
    incident_id: str | None = None,
    dashboard_url: str = "",
) -> dict[str, Any]:
    """
    Full entry point — creates a branch, optionally commits a patch, opens a PR.

    Returns:
        {"success": True,  "pr_url": ..., "pr_number": ..., "branch": ...}
        {"success": False, "error": ...}
    """
    token     = Config.GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    repo_name = Config.GITHUB_REPO  or os.getenv("GITHUB_REPO", "")

    if not token or not repo_name or token in ("dummy", "your-token-here"):
        logger.warning("GitHub PR skipped — GITHUB_TOKEN or GITHUB_REPO not configured")
        return {"success": False, "error": "GITHUB_TOKEN / GITHUB_REPO not configured"}

    try:
        from github import Github, GithubException  # type: ignore[import]
    except ImportError:
        return {"success": False, "error": "PyGithub not installed — run: pip install PyGithub"}

    # ── Unpack RCA fields ───────────────────────────────────────────────────
    trace_id       = rca.get("trace_id") or incident.get("trace_id", "unknown")
    classification = rca.get("classification", "Unknown Issue")
    root_cause     = rca.get("root_cause", "")
    blast_radius   = rca.get("blast_radius", "LOW")
    confidence     = float(rca.get("confidence_score") or 0)
    impact         = rca.get("impact", "See logs for details")
    suggested_fix  = rca.get("suggested_fix", {})
    patch          = suggested_fix.get("patch", "")
    target_class   = suggested_fix.get("target_class", "")
    rationale      = suggested_fix.get("rationale", "")
    tests          = suggested_fix.get("tests", [])
    github_meta    = rca.get("github_pr", {})
    signals        = rca.get("log_signals", {})

    branch_name = (
        "morphic/fix-"
        + re.sub(r"[^a-zA-Z0-9_-]", "-", trace_id[:20])
    )
    pr_title = (
        github_meta.get("title")
        or f"[Morphic] {classification[:60]} [{trace_id[:8]}]"
    )
    labels: list[str] = github_meta.get("labels", ["morphic-auto", "incident-fix"])

    # ── Connect via PyGithub ────────────────────────────────────────────────
    try:
        g    = Github(token)
        repo = g.get_repo(repo_name)
    except Exception as exc:
        logger.warning("PyGithub: cannot connect to repo %s: %s", repo_name, exc)
        return {"success": False, "error": f"Cannot access repo: {exc}"}

    default_branch = repo.default_branch

    # ── Create branch ───────────────────────────────────────────────────────
    try:
        base_sha = repo.get_branch(default_branch).commit.sha
        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        logger.info("Branch created: %s", branch_name)
    except GithubException as exc:
        if exc.status == 422:
            logger.info("Branch %s already exists — reusing", branch_name)
        else:
            logger.warning("Branch creation failed: %s", exc)
            return {"success": False, "error": f"Branch creation failed: {exc}"}
    except Exception as exc:
        logger.warning("Branch creation failed: %s", exc)
        return {"success": False, "error": f"Branch creation failed: {exc}"}

    # ── Commit patch (optional — skip gracefully if file not found) ─────────
    if patch and target_class:
        try:
            java_file = find_java_file(repo, target_class)
            if java_file:
                original_content = java_file.decoded_content.decode("utf-8", errors="replace")
                new_content      = apply_patch(original_content, patch)
                commit_msg = (
                    f"fix({target_class}): {classification[:50]} [Morphic AI]\n\n"
                    f"Trace-ID: {trace_id}\n"
                    f"Blast-Radius: {blast_radius}\n"
                    f"Confidence: {confidence:.0%}"
                )
                repo.update_file(
                    java_file.path,
                    commit_msg,
                    new_content,
                    java_file.sha,
                    branch=branch_name,
                )
                logger.info("Patch committed to %s on branch %s", java_file.path, branch_name)
            else:
                logger.info(
                    "Target class %s not found in repo — opening PR without file commit",
                    target_class,
                )
        except Exception as exc:
            logger.warning("Could not commit patch to %s: %s", target_class, exc)
            # Non-fatal — still open the PR

    # ── Build PR body ───────────────────────────────────────────────────────
    incident_url = f"{dashboard_url}/incidents?trace={trace_id}" if dashboard_url else ""
    tests_md = "\n".join(f"- `{t}`" for t in tests) or "- No tests specified"
    signals_rows = "\n".join(
        f"| {k.replace('_',' ').title()} | `{v}` |"
        for k, v in signals.items() if v
    )

    pr_body = f"""## 🤖 Morphic AI — Automated Fix

**Incident:** {classification}
**Trace ID:** `{trace_id}`
**Blast Radius:** {blast_radius}
**Confidence:** {confidence * 100:.0f}%

### Root Cause
{root_cause}

### Impact
{impact}

### Log Signals
| Field | Value |
|-------|-------|
{signals_rows or "| — | — |"}

### Suggested Fix — `{target_class or "unknown"}`
{f"**Rationale:** {rationale}" if rationale else ""}

```java
{patch[:2000] if patch else "// See RCA for full patch"}
```

### Suggested Tests
{tests_md}

---
{f"📊 [View Incident on Dashboard]({incident_url})" if incident_url else ""}

{github_meta.get("body", "")}

---
*Auto-generated by [Morphic](https://github.com) Self-Healing Incident Assistant.*
*Do NOT merge without human review.*
"""

    # ── Open PR ─────────────────────────────────────────────────────────────
    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch,
        )
        logger.info("PR #%d created: %s for trace_id=%s", pr.number, pr.html_url, trace_id)
    except GithubException as exc:
        # 422 = PR already exists for this branch
        if exc.status == 422:
            logger.info("PR for branch %s already open — skipping duplicate", branch_name)
            # Try to find the existing PR URL
            try:
                pulls = repo.get_pulls(head=f"{repo.owner.login}:{branch_name}", state="open")
                existing = next(iter(pulls), None)
                if existing:
                    return {"success": True, "pr_url": existing.html_url,
                            "pr_number": existing.number, "branch": branch_name}
            except Exception:
                pass
        logger.warning("PR creation failed: %s", exc)
        return {"success": False, "error": f"PR creation failed: {exc}"}
    except Exception as exc:
        logger.warning("PR creation failed: %s", exc)
        return {"success": False, "error": f"PR creation failed: {exc}"}

    # Apply labels (best effort)
    if labels:
        try:
            pr.add_to_labels(*labels)
        except Exception as exc:
            logger.debug("Label application failed (non-fatal): %s", exc)

    pr_url    = pr.html_url
    pr_number = pr.number

    # Record action in DB
    if incident_id:
        try:
            action_row = postgres.insert_action({
                "incident_id": incident_id,
                "action_type": "github_pr",
                "status":      "running",
                "details":     {"pr_url": pr_url, "pr_number": pr_number,
                                "branch": branch_name, "link": pr_url},
            })
            postgres.complete_action(
                str(action_row["id"]),
                "completed",
                {"pr_url": pr_url, "pr_number": pr_number,
                 "branch": branch_name, "link": pr_url, "summary": pr_title},
            )
        except Exception as exc:
            logger.warning("Failed to record github_pr action in DB: %s", exc)

    return {
        "success":   True,
        "pr_url":    pr_url,
        "pr_number": pr_number,
        "branch":    branch_name,
        "error":     None,
    }
