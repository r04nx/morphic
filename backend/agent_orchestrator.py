#!/usr/bin/env python3
"""
Morphic Agent Orchestrator
==========================================
On anomaly detection:
  1. Creates a trace-scoped work directory
  2. Clones the monitor's GitHub repository
  3. Invokes Claude Code CLI programmatically with FULL feature set
     (--output-format stream-json, --system-prompt, MCP integration, etc.)
  4. Generates an RCA.md and automatically pushes a fix PR
"""

import os
import json
import uuid
import shutil
import logging
import subprocess
import threading
import textwrap
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("morphic.agent_orchestrator")

# ─────────────────────────────────────────────────────────────
# Advanced System Prompts
# ─────────────────────────────────────────────────────────────

SRE_SYSTEM_PROMPT = textwrap.dedent("""
You are a highly autonomous Site Reliability Engineer (SRE) and AI Agent running within the Morphic self-healing pipeline. 
An anomaly has been detected and you have been triggered to perform Root Cause Analysis (RCA) and automated remediation.

## Operating Procedures
1. **Analyze Signals**: You are provided with log entries and anomaly metrics. Read them carefully to identify the core failure mode.
2. **Codebase Inspection**: The repository has been cloned. Use your allowed tools to search the codebase and locate the origin of the error.
3. **Draft Fix**: Write a minimal, robust fix that directly addresses the root cause without side effects.
4. **Create PR**: Use the `mcp__github__create_branch`, `mcp__github__push_files`, and `mcp__github__create_pull_request` tools to push your fix.
5. **RCA Generation**: Create an `RCA.md` file in the root of the workspace detailing the incident timeline, root cause, blast radius, and your fix.

## Constraint Checklist
- Do NOT hallucinate variables or configurations that aren't in the codebase.
- PR messages must follow Conventional Commits (e.g., `fix(module): resolved timeout issue`).
- The `RCA.md` must be comprehensive and technical.
- You operate in `bypassPermissions` mode. Ensure all changes are safe and correctly tested.
""").strip()

# ─────────────────────────────────────────────────────────────
# Agent Run Manager
# ─────────────────────────────────────────────────────────────

class AgentOrchestrator:
    """Manages full-featured Claude Code CLI invocations."""

    TMP_BASE = Path("/tmp/morphic-agents")

    def __init__(self, db_manager):
        self.db = db_manager
        self.TMP_BASE.mkdir(parents=True, exist_ok=True)
        # Create a default MCP config for GitHub tool availability
        self.mcp_config_path = self.TMP_BASE / "claude-mcp.json"
        self._ensure_mcp_config()

    def _ensure_mcp_config(self):
        """Ensure MCP configuration file exists so Claude Code can load the GitHub server."""
        if not self.mcp_config_path.exists():
            cfg = {
                "mcpServers": {
                    "github": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"]
                    }
                }
            }
            self.mcp_config_path.write_text(json.dumps(cfg, indent=2))

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def trigger_async(
        self,
        monitor_id: str,
        trace_id: str,
        logs: List[Dict],
        analysis: Dict,
        github_repo: Optional[str] = None,
        github_token: Optional[str] = None,
        github_branch: str = "main",
    ) -> str:
        run_id = str(uuid.uuid4())
        self._create_run(run_id, monitor_id, trace_id, logs, analysis, github_repo)

        thread = threading.Thread(
            target=self._execute_run,
            args=(run_id, monitor_id, trace_id, logs, analysis, github_repo, github_token, github_branch),
            name=f"agent-{run_id[:8]}",
            daemon=True,
        )
        thread.start()
        logger.info(f"[orchestrator] ▶ Triggered agent run {run_id} for trace {trace_id}")
        return run_id

    # ------------------------------------------------------------------ #
    #  DB Methods
    # ------------------------------------------------------------------ #
    def _create_run(self, run_id, monitor_id, trace_id, logs, analysis, github_repo) -> Dict:
        try:
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_runs
                        (id, monitor_id, trace_id, status, log_snapshot, anomalies, github_repo)
                    VALUES (%s, %s, %s, 'QUEUED', %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        run_id,
                        monitor_id,
                        trace_id,
                        json.dumps(logs[-50:]),
                        json.dumps(analysis),
                        github_repo,
                    ),
                )
            self.db.postgres_conn.commit()
        except Exception as exc:
            logger.error(f"[orchestrator] DB error: {exc}")
            try:
                self.db.postgres_conn.rollback()
            except Exception:
                pass
        return {"id": run_id}

    def _update_run(self, run_id: str, **kwargs):
        if not kwargs:
            return
        fields = ", ".join(f"{k}=%s" for k in kwargs)
        values = list(kwargs.values()) + [run_id]
        try:
            with self.db.postgres_conn.cursor() as cur:
                cur.execute(f"UPDATE agent_runs SET {fields} WHERE id=%s", values)
            self.db.postgres_conn.commit()
        except Exception:
            try:
                self.db.postgres_conn.rollback()
            except Exception:
                pass

    def list_runs(self, monitor_id: str, limit: int = 10) -> List[Dict]:
        try:
            from psycopg2.extras import RealDictCursor
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM agent_runs WHERE monitor_id=%s ORDER BY triggered_at DESC LIMIT %s""",
                    (monitor_id, limit),
                )
                rows = cur.fetchall()
                res = []
                for r in rows:
                    d = dict(r)
                    for k in ("triggered_at", "completed_at"):
                        if d.get(k): d[k] = d[k].isoformat()
                    res.append(d)
                return res
        except Exception:
            return []

    def get_run(self, run_id: str) -> Optional[Dict]:
        try:
            from psycopg2.extras import RealDictCursor
            with self.db.postgres_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM agent_runs WHERE id=%s", (run_id,))
                r = cur.fetchone()
                if not r: return None
                d = dict(r)
                for k in ("triggered_at", "completed_at"):
                    if d.get(k): d[k] = d[k].isoformat()
                return d
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    #  Execution
    # ------------------------------------------------------------------ #
    def _execute_run(
        self,
        run_id: str,
        monitor_id: str,
        trace_id: str,
        logs: List[Dict],
        analysis: Dict,
        github_repo: Optional[str],
        github_token: Optional[str],
        github_branch: str,
    ):
        work_dir = self.TMP_BASE / trace_id
        try:
            self._update_run(run_id, status="RUNNING", work_dir=str(work_dir))
            work_dir.mkdir(parents=True, exist_ok=True)

            # Context preparation
            context_file = work_dir / "INCIDENT_CONTEXT.md"
            context_text = self._build_context(trace_id, logs, analysis, github_repo, github_branch)
            context_file.write_text(context_text, encoding="utf-8")

            # Git clone
            repo_dir = None
            if github_repo:
                repo_dir = self._clone_repo(work_dir, github_repo, github_token, github_branch)
            
            cwd = str(repo_dir) if repo_dir else str(work_dir)
            self._update_run(run_id, status="ANALYZING")

            # Execute full Claude Code CLI pipeline
            claude_output = self._invoke_claude_full(cwd, str(context_file), github_token)

            # Read RCA output
            rca_md = ""
            rca_path = Path(cwd) / "RCA.md"
            if rca_path.exists():
                rca_md = rca_path.read_text(encoding="utf-8")

            # Extract PR details
            pr_url, pr_num = self._extract_pr_info(claude_output)
            summary = self._build_summary(analysis, claude_output)

            status = "PR_CREATED" if pr_url else ("COMPLETED" if rca_md else "ANALYZED")

            self._update_run(
                run_id,
                status=status,
                completed_at=datetime.now(timezone.utc),
                github_pr_url=pr_url,
                github_pr_number=pr_num,
                rca_summary=summary,
                rca_md=rca_md,
                claude_output=claude_output[:25000],
            )
            logger.info(f"[orchestrator] ✅ Agent {run_id} finished. PR: {pr_url}")

            # Update monitor
            try:
                with self.db.postgres_conn.cursor() as cur:
                    cur.execute("UPDATE monitors SET agent_run_status=%s WHERE id=%s", (status, monitor_id))
                self.db.postgres_conn.commit()
            except Exception:
                pass

        except Exception as exc:
            logger.error(f"[orchestrator] Agent {run_id} failed: {exc}", exc_info=True)
            self._update_run(run_id, status="FAILED", error_message=str(exc)[:2000])

    # ------------------------------------------------------------------ #
    #  CLI Invocation
    # ------------------------------------------------------------------ #
    def _invoke_claude_full(self, cwd: str, context_file: str, github_token: Optional[str]) -> str:
        """
        Invokes Claude Code utilizing the full suite of CLI features:
        - Stream JSON output for programmatic parsing
        - Bypass permissions for full autonomy
        - MCP configuration for GitHub integration
        - Explicit system prompt overrides
        - Disallowed tools to enforce scope (no destructive base commands outside git)
        """
        env = os.environ.copy()
        if github_token:
            # Inject token for the GitHub MCP server
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token
            env["GITHUB_TOKEN"] = github_token

        # Build the command using all documented flags
        cmd = [
            "claude",
            "--print",                             # Headless execution
            "--output-format", "stream-json",      # Rich streaming json output
            "--permission-mode", "bypassPermissions", # Autonomy
            "--mcp-config", str(self.mcp_config_path), # GitHub MCP Server
            "--system-prompt", SRE_SYSTEM_PROMPT,  # SRE Persona
            "--disallowed-tools", "rmdir,rm,mkfs", # Deny highly destructive shell commands
            "--effort", "high",                    # Maximize reasoning capability
            "--max-turns", "40",                   # Allow deep debugging loops
            "--model", os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet"),
            "-p", f"Please process the incident defined in {context_file} and perform RCA and remediation."
        ]

        logger.info(f"[orchestrator] Executing: {' '.join(cmd)}")
        
        full_output = []
        try:
            # We stream the JSON to parse it dynamically (and log progress)
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Consume stream-json stdout
            for line in proc.stdout:
                if line.strip():
                    full_output.append(line)
                    try:
                        # Attempt to parse stream chunks for live progress (optional logging)
                        event = json.loads(line)
                        if event.get("type") == "message" and event.get("content"):
                            # Just capture the text for the final output blob
                            pass
                    except json.JSONDecodeError:
                        pass

            proc.wait(timeout=900) # 15 minute hard timeout
            
            stderr = proc.stderr.read()
            if proc.returncode != 0:
                logger.warning(f"[orchestrator] Claude returned {proc.returncode}. Stderr: {stderr}")

            # Combine output streams for the DB record
            combined_output = "".join(full_output) + ("\nSTDERR:\n" + stderr if stderr else "")
            return combined_output

        except subprocess.TimeoutExpired:
            logger.error("[orchestrator] Claude CLI Timeout (900s)")
            proc.kill()
            return "ERROR: Claude CLI execution timed out."
        except Exception as exc:
            logger.error(f"[orchestrator] Subprocess error: {exc}")
            return f"ERROR: {exc}"

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _clone_repo(self, work_dir: Path, repo: str, token: Optional[str], branch: str) -> Optional[Path]:
        repo_dir = work_dir / "repo"
        url = repo if "://" in repo else f"https://github.com/{repo}.git"
        if token and "://" in url:
            url = url.replace("://", f"://{token}@")
            
        try:
            res = subprocess.run(
                ["git", "clone", "--depth=1", "--branch", branch, url, str(repo_dir)],
                capture_output=True, text=True, timeout=60
            )
            if res.returncode == 0:
                return repo_dir
            logger.error(f"Clone failed: {res.stderr}")
        except Exception as e:
            logger.error(f"Clone err: {e}")
        return None

    def _build_context(self, trace_id, logs, analysis, repo, branch) -> str:
        signals = json.dumps(analysis.get("signals", [])[:10], indent=2)
        raw_logs = json.dumps(logs[-30:], indent=2)
        return f"""
# Incident Context
**Trace ID:** {trace_id}
**Repository:** {repo or 'None'} (Branch: {branch})

## Anomaly Metrics
- Score: {analysis.get('score', 0)}
- Pipeline: {analysis.get('pipeline', 'unknown')}
- Time-Series Anomaly: {analysis.get('ts_anomaly', False)}
- Error Rate: {analysis.get('error_rate', 0):.2%}

## Key Error Signals
```json
{signals}
```

## Raw Log Context
```json
{raw_logs}
```
"""

    def _extract_pr_info(self, output: str):
        import re
        match = re.search(r'https://github\.com/[^/]+/[^/]+/pull/(\d+)', output)
        if match: return match.group(0), int(match.group(1))
        return None, None

    def _build_summary(self, analysis: Dict, output: str) -> str:
        score = analysis.get("score", 0)
        signals = analysis.get("signals", [])
        msg = signals[0]["message"][:150] if signals else "No specific error captured."
        return f"Score {score:.2f} | {msg}"
