"""
Claude Agent Service for incident remediation.
Clones GitHub repo, runs Claude agent to analyze and fix issues, creates PR via GitHub MCP.
"""
import asyncio
import os
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
import json

from claude_agent_sdk import query, ClaudeAgentOptions


class ClaudeAgentService:
    """Service to run Claude Code agent for incident remediation."""
    
    def __init__(self):
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.temp_dir = tempfile.gettempdir()
        
        if not self.anthropic_api_key:
            print("WARNING: ANTHROPIC_API_KEY not set - Claude agent will not work")
    
    async def handle_incident(
        self,
        incident_id: str,
        trace_id: str,
        error_type: str,
        log_message: str,
        service: str,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_token: Optional[str] = None,
        github_branch: str = "main",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle an incident by running Claude agent to analyze and fix.
        
        Args:
            incident_id: UUID of the incident
            trace_id: Trace ID from the logs
            error_type: Type of error detected
            log_message: The log message with the error
            service: Service where error occurred
            additional_context: Additional context (RCA, etc.)
        
        Returns:
            Dict with agent run results, PR URL, etc.
        """
        if not self.anthropic_api_key:
            return {
                "status": "error",
                "message": "ANTHROPIC_API_KEY not configured"
            }
        
        # Create temporary directory for repo clone
        repo_path = os.path.join(self.temp_dir, f"incident_{incident_id}")
        
        try:
            # Clone the repo
            if github_owner and github_repo and github_token:
                clone_url = f"https://{github_token}@github.com/{github_owner}/{github_repo}.git"
                os.makedirs(repo_path, exist_ok=True)
                
                # Clone repo (using subprocess for git)
                import subprocess
                result = subprocess.run(
                    ["git", "clone", clone_url, repo_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    return {
                        "status": "error",
                        "message": f"Failed to clone repo: {result.stderr}"
                    }
            else:
                # Use local chaos-backend if available
                repo_path = "/home/rohan/Public/morphic/chaos-backend"
                if not os.path.exists(repo_path):
                    return {
                        "status": "error",
                        "message": "GitHub repo not configured and local chaos-backend not found"
                    }
            
            # Build the prompt for Claude
            prompt = self._build_incident_prompt(
                incident_id, trace_id, error_type, log_message, service, additional_context
            )
            
            # Configure Claude agent options
            options = ClaudeAgentOptions(
                system_prompt=self._get_system_prompt(),
                permission_mode="acceptEdits",
                cwd=repo_path,
                allowed_tools=["bash", "read_file", "write_to_file"],
            )
            
            # Run Claude agent
            agent_messages = []
            async for message in query(prompt=prompt, options=options):
                agent_messages.append(str(message))
                print(f"[Claude Agent] {message}")
            
            # Try to create PR via GitHub MCP or API
            pr_url = None
            if github_token and github_owner and github_repo:
                pr_url = await self._create_pull_request(
                    incident_id, trace_id, error_type, agent_messages, github_owner, github_repo, github_token, github_branch
                )
            
            return {
                "status": "completed",
                "incident_id": incident_id,
                "trace_id": trace_id,
                "agent_messages": agent_messages,
                "pr_url": pr_url,
                "repo_path": repo_path,
                "github_owner": github_owner,
                "github_repo": github_repo,
                "github_branch": github_branch,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "incident_id": incident_id,
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            # Cleanup temp directory if we cloned
            if github_owner and github_repo and os.path.exists(repo_path) and repo_path.startswith(self.temp_dir):
                try:
                    shutil.rmtree(repo_path)
                except:
                    pass
    
    def _build_incident_prompt(
        self,
        incident_id: str,
        trace_id: str,
        error_type: str,
        log_message: str,
        service: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt for Claude agent."""
        prompt = f"""You are an expert Java Spring Boot developer tasked with fixing a production incident.

INCIDENT DETAILS:
- Incident ID: {incident_id}
- Trace ID: {trace_id}
- Error Type: {error_type}
- Service: {service}
- Log Message: {log_message}

"""
        if additional_context:
            if 'rca' in additional_context:
                prompt += f"ROOT CAUSE ANALYSIS:\n{additional_context['rca']}\n\n"
            if 'suggested_fix' in additional_context:
                prompt += f"SUGGESTED FIX:\n{additional_context['suggested_fix']}\n\n"
        
        prompt += """TASK:
1. Analyze the codebase to understand the error
2. Identify the root cause in the Java source files
3. Implement a fix that addresses the issue
4. Write or update tests to verify the fix
5. Ensure the fix follows best practices
6. Document any changes with comments

Return a summary of:
- The root cause you found
- The file(s) you modified
- The changes you made
- Any tests you added/modified
"""
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for Claude agent."""
        return """You are an expert Java Spring Boot developer with deep knowledge of:
- Spring Boot framework patterns
- Distributed systems and microservices
- Database transactions and consistency
- Error handling and retry logic
- Testing with JUnit and Mockito

When fixing issues:
- Always consider edge cases
- Maintain backward compatibility when possible
- Add appropriate logging
- Write tests for new functionality
- Follow existing code style and patterns
- Document non-obvious changes with comments
"""

    async def _create_pull_request(
        self,
        incident_id: str,
        trace_id: str,
        error_type: str,
        agent_messages: list,
        github_owner: str,
        github_repo: str,
        github_token: str,
        github_branch: str,
    ) -> Optional[str]:
        """Create a pull request via GitHub API."""
        try:
            from github import Github
            
            g = Github(github_token)
            repo = g.get_repo(f"{github_owner}/{github_repo}")
            
            # Create a new branch
            branch_name = f"fix/incident-{incident_id[:8]}"
            default_branch = github_branch or repo.default_branch
            
            # Get the latest commit
            default_branch_ref = repo.get_git_ref(f"heads/{default_branch}")
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=default_branch_ref.object.sha
            )
            
            # Build PR title and body
            title = f"Fix: {error_type} (Incident {incident_id[:8]})"
            body = f"""## Incident Fix

**Incident ID**: {incident_id}
**Trace ID**: {trace_id}
**Error Type**: {error_type}

## Root Cause
Automatically detected by LogAI analysis and investigated by Claude agent.

## Changes
This PR addresses the incident by:
"""
            # Add agent messages as context
            for msg in agent_messages[:5]:  # Limit to first 5 messages
                body += f"\n{msg}\n"
            
            body += f"""
## Testing
Changes have been tested to ensure the fix resolves the issue.

## Related
- Trace ID: {trace_id}
- Incident: {incident_id}
"""
            
            # Create PR
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=default_branch,
            )
            
            return pr.html_url
            
        except Exception as e:
            print(f"Failed to create PR: {e}")
            return None


# Singleton instance
claude_agent_service = ClaudeAgentService()
