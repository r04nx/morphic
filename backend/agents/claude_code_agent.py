#!/usr/bin/env python3
"""
Claude Code Agent Invoker with GitHub MCP Server Integration

This script provides a Python interface to invoke Claude Code agents with:
- Directory-based project analysis
- Custom system prompts
- GitHub MCP server integration
- Comprehensive logging
- Agent event tracking
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from claude_agent_sdk import query, ClaudeAgentOptions


class AgentLogger:
    """Comprehensive logging for Claude Code Agent sessions"""
    
    def __init__(self, log_dir: str = "agent_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup main logger
        self.logger = logging.getLogger("claude_agent")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler for detailed logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"agent_session_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler for progress
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Session data storage
        self.session_data = {
            "start_time": datetime.now().isoformat(),
            "messages": [],
            "tool_calls": [],
            "errors": [],
            "files_modified": [],
            "rca_analysis": None,
            "log_data": {}
        }
        
    def log_message(self, message_type: str, content: Any):
        """Log agent messages"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": message_type,
            "content": content
        }
        self.session_data["messages"].append(log_entry)
        self.logger.info(f"[{message_type}] {content}")
    
    def log_tool_call(self, tool_name: str, parameters: Dict, result: Any = None):
        """Log tool execution"""
        timestamp = datetime.now().isoformat()
        tool_entry = {
            "timestamp": timestamp,
            "tool": tool_name,
            "parameters": parameters,
            "result": str(result) if result else None
        }
        self.session_data["tool_calls"].append(tool_entry)
        self.logger.debug(f"[TOOL] {tool_name}: {parameters}")
    
    def log_error(self, error: Exception, context: str = ""):
        """Log errors with context"""
        timestamp = datetime.now().isoformat()
        error_entry = {
            "timestamp": timestamp,
            "context": context,
            "error": str(error),
            "error_type": type(error).__name__
        }
        self.session_data["errors"].append(error_entry)
        self.logger.error(f"[ERROR] {context}: {error}")
    
    def log_file_modification(self, file_path: str, action: str):
        """Log file modifications"""
        timestamp = datetime.now().isoformat()
        file_entry = {
            "timestamp": timestamp,
            "file": file_path,
            "action": action
        }
        self.session_data["files_modified"].append(file_entry)
        self.logger.info(f"[FILE] {action}: {file_path}")
    
    def save_session_summary(self, project_dir: str, system_prompt: str):
        """Save comprehensive session summary"""
        self.session_data.update({
            "end_time": datetime.now().isoformat(),
            "project_directory": project_dir,
            "system_prompt": system_prompt,
            "total_messages": len(self.session_data["messages"]),
            "total_tool_calls": len(self.session_data["tool_calls"]),
            "total_errors": len(self.session_data["errors"]),
            "files_modified_count": len(self.session_data["files_modified"])
        })
        
        # Save session summary as JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.log_dir / f"session_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        self.logger.info(f"Session summary saved to: {summary_file}")


class ClaudeCodeAgentInvoker:
    """Main class for invoking Claude Code Agents with GitHub MCP integration"""
    
    def __init__(self, project_dir: str, system_prompt: str, log_dir: str = "agent_logs"):
        self.project_dir = Path(project_dir).resolve()
        self.system_prompt = system_prompt
        self.logger = AgentLogger(log_dir)
        self.log_data = {}
        
        # Validate project directory
        if not self.project_dir.exists():
            raise ValueError(f"Project directory does not exist: {self.project_dir}")
        
        self.logger.log_message("INIT", f"Initialized agent for project: {self.project_dir}")
    
    def create_agent_options(self) -> ClaudeAgentOptions:
        """Create Claude Agent options with GitHub MCP server"""
        
        # GitHub MCP server configuration
        github_mcp_config = {
            "name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            }
        }
        
        # Filter out empty environment variables
        if not github_mcp_config["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"]:
            self.logger.log_message("WARNING", "GITHUB_PERSONAL_ACCESS_TOKEN not set, GitHub MCP features will be limited")
            github_mcp_config = None
        
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            permission_mode="acceptEdits",  # Allows the agent to propose file edits
            cwd=str(self.project_dir),
            allowed_tools=["Read", "Write", "Bash", "Edit"],  # Specify allowed tools
            mcp_servers=[github_mcp_config] if github_mcp_config else []
        )
        
        self.logger.log_message("CONFIG", f"Agent options created with MCP servers: {bool(github_mcp_config)}")
        return options
    
    async def execute_task(self, task_prompt: str) -> Dict[str, Any]:
        """Execute a task with the Claude Code Agent"""
        
        self.logger.log_message("TASK_START", f"Executing task: {task_prompt}")
        
        try:
            options = self.create_agent_options()
            
            execution_results = {
                "task": task_prompt,
                "start_time": datetime.now().isoformat(),
                "messages": [],
                "tool_calls": [],
                "success": False,
                "error": None
            }
            
            # Execute the agent loop
            async for message in query(prompt=task_prompt, options=options):
                message_type = getattr(message, 'type', 'unknown')
                message_content = str(message)
                
                execution_results["messages"].append({
                    "type": message_type,
                    "content": message_content,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.logger.log_message("AGENT_MESSAGE", f"[{message_type}] {message_content}")
                
                # Log tool calls if present
                if hasattr(message, 'tool_calls'):
                    for tool_call in message.tool_calls:
                        self.logger.log_tool_call(
                            tool_call.get('name', 'unknown'),
                            tool_call.get('arguments', {}),
                            tool_call.get('result')
                        )
                        execution_results["tool_calls"].append(tool_call)
            
            execution_results["success"] = True
            execution_results["end_time"] = datetime.now().isoformat()
            
            self.logger.log_message("TASK_COMPLETE", "Task completed successfully")
            return execution_results
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            self.logger.log_error(e, "Task execution")
            execution_results["error"] = error_msg
            execution_results["end_time"] = datetime.now().isoformat()
            return execution_results
    
    async def analyze_project(self, analysis_prompt: str = None) -> Dict[str, Any]:
        """Analyze the project directory with Claude Code Agent"""
        
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this codebase and provide:
            1. Project structure overview
            2. Main technologies and frameworks used
            3. Key files and their purposes
            4. Potential issues or improvements
            5. Dependencies and build configuration
            
            Please be thorough but concise in your analysis.
            """
        
        return await self.execute_task(analysis_prompt)
    
    def parse_logs(self, log_input: str) -> Dict[str, Any]:
        """Parse logs from various input formats (file, string, or directory)"""
        log_path = Path(log_input)
        
        if log_path.is_file():
            # Read from file
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
        elif log_path.is_dir():
            # Read all log files from directory
            log_content = ""
            for log_file in log_path.glob("*.log"):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content += f"\n=== {log_file.name} ===\n"
                    log_content += f.read() + "\n"
        else:
            # Treat as direct log content string
            log_content = log_input
        
        # Parse log entries
        log_entries = []
        error_patterns = [
            r'\[(ERROR|WARN|CRITICAL|FATAL)\]',
            r'Exception:',
            r'Traceback',
            r'Failed',
            r'Timeout',
            r'Connection',
            r'NullPointer',
            r'OutOfMemory'
        ]
        
        lines = log_content.split('\n')
        for i, line in enumerate(lines):
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in error_patterns):
                # Extract context around error
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 3)
                context = lines[context_start:context_end]
                
                log_entries.append({
                    'line_number': i + 1,
                    'timestamp': self._extract_timestamp(line),
                    'level': self._extract_log_level(line),
                    'message': line.strip(),
                    'context': context,
                    'trace_id': self._extract_trace_id(line)
                })
        
        self.log_data = {
            'total_lines': len(lines),
            'error_entries': log_entries,
            'raw_content': log_content,
            'parsed_at': datetime.now().isoformat()
        }
        
        self.logger.log_message("LOG_PARSE", f"Parsed {len(log_entries)} error entries from {len(lines)} log lines")
        return self.log_data
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line"""
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',
            r'\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        return None
    
    def _extract_log_level(self, line: str) -> str:
        """Extract log level from log line"""
        levels = ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG']
        for level in levels:
            if level in line.upper():
                return level
        return 'UNKNOWN'
    
    def _extract_trace_id(self, line: str) -> Optional[str]:
        """Extract trace ID from log line"""
        trace_patterns = [
            r'trace[_-]?id[=:]\s*([\w-]+)',
            r'trace[_-]?id[=:]\s*"([\w-]+)"',
            r'\[([\w-]{8,})\]',  # UUID-like patterns
            r'correlation[_-]?id[=:]\s*([\w-]+)'
        ]
        
        for pattern in trace_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        return None
    
    async def perform_rca(self, log_input: str, custom_prompt: str = None) -> Dict[str, Any]:
        """Perform Root Cause Analysis based on logs and suggest fixes"""
        
        self.logger.log_message("RCA_START", "Starting Root Cause Analysis")
        
        # Parse logs
        log_data = self.parse_logs(log_input)
        
        # Build RCA prompt
        rca_prompt = self._build_rca_prompt(log_data, custom_prompt)
        
        # Execute RCA analysis
        rca_results = await self.execute_task(rca_prompt)
        
        # Enhance results with log analysis
        rca_results['log_analysis'] = {
            'total_errors': len(log_data['error_entries']),
            'error_patterns': self._analyze_error_patterns(log_data['error_entries']),
            'affected_components': self._identify_affected_components(log_data['error_entries']),
            'timeline': self._build_error_timeline(log_data['error_entries'])
        }
        
        # Store RCA in session data
        self.logger.session_data['rca_analysis'] = rca_results
        self.logger.session_data['log_data'] = log_data
        
        self.logger.log_message("RCA_COMPLETE", f"RCA completed with {len(log_data['error_entries'])} errors analyzed")
        return rca_results
    
    def _build_rca_prompt(self, log_data: Dict[str, Any], custom_prompt: str = None) -> str:
        """Build comprehensive RCA prompt from log data"""
        
        base_prompt = """
You are an expert SRE (Site Reliability Engineer) and senior developer performing Root Cause Analysis (RCA) on production incidents.

Your task is to:
1. Analyze the provided log data and identify the root cause
2. Determine the blast radius and impact severity (LOW/MEDIUM/HIGH/CRITICAL)
3. Provide specific code fixes, file modifications, and patches
4. Create actionable remediation steps
5. Generate test cases to verify the fix

LOG DATA:
{log_summary}

ERROR ENTRIES:
{error_entries}

ANALYSIS REQUIREMENTS:
1. **Root Cause**: Identify the exact technical root cause with evidence from logs
2. **Impact Assessment**: Classify severity and affected systems
3. **Code Fixes**: Provide specific file paths, line numbers, and exact code changes
4. **Patches**: Generate ready-to-apply patches in diff format
5. **Verification**: Include test cases and validation steps
6. **Prevention**: Suggest monitoring and prevention measures

Focus on these incident types:
- Gateway Timeout resulting in duplicate payments
- Partial Write leading to orphaned payment records  
- Race Condition causing negative stock levels
- Async Trace Loss due to MDC propagation failures
- Inconsistent Order State (orders stuck in CREATED)

OUTPUT FORMAT:
Respond with a structured JSON RCA document:
{{
  "classification": "string",
  "root_cause": "string", 
  "blast_radius": "LOW|MEDIUM|HIGH|CRITICAL",
  "impact": "string",
  "trace_id": "string",
  "timestamp": "string",
  "log_signals": {{
    "service": "string",
    "endpoint": "string", 
    "exception_class": "string",
    "error_message": "string"
  }},
  "suggested_fix": {{
    "language": "java",
    "target_class": "string",
    "patch": "string",
    "rationale": "string",
    "tests": ["string"]
  }},
  "github_pr": {{
    "title": "string",
    "body": "string", 
    "labels": ["string"]
  }},
  "confidence_score": 0.0
}}
        """.format(
            log_summary=json.dumps({
                'total_lines': log_data['total_lines'],
                'error_count': len(log_data['error_entries']),
                'parsed_at': log_data['parsed_at']
            }, indent=2),
            error_entries=json.dumps(log_data['error_entries'][:10], indent=2)  # Limit to first 10 errors
        )
        
        if custom_prompt:
            base_prompt += f"\n\nADDITIONAL CONTEXT:\n{custom_prompt}"
        
        return base_prompt
    
    def _analyze_error_patterns(self, error_entries: List[Dict]) -> Dict[str, int]:
        """Analyze common error patterns"""
        patterns = {}
        for entry in error_entries:
            message = entry['message'].lower()
            if 'timeout' in message:
                patterns['timeout'] = patterns.get('timeout', 0) + 1
            elif 'connection' in message:
                patterns['connection'] = patterns.get('connection', 0) + 1
            elif 'null' in message:
                patterns['null_pointer'] = patterns.get('null_pointer', 0) + 1
            elif 'memory' in message:
                patterns['memory'] = patterns.get('memory', 0) + 1
            elif 'exception' in message:
                patterns['exception'] = patterns.get('exception', 0) + 1
        return patterns
    
    def _identify_affected_components(self, error_entries: List[Dict]) -> List[str]:
        """Identify affected components from logs"""
        components = set()
        for entry in error_entries:
            message = entry['message']
            # Extract component names from log messages
            if 'payment' in message.lower():
                components.add('payment-service')
            if 'order' in message.lower():
                components.add('order-service')
            if 'inventory' in message.lower():
                components.add('inventory-service')
            if 'gateway' in message.lower():
                components.add('api-gateway')
        return list(components)
    
    def _build_error_timeline(self, error_entries: List[Dict]) -> List[Dict]:
        """Build chronological timeline of errors"""
        timeline = []
        for entry in sorted(error_entries, key=lambda x: x.get('timestamp', '')):
            timeline.append({
                'timestamp': entry.get('timestamp'),
                'level': entry.get('level'),
                'message': entry.get('message')[:100] + '...' if len(entry.get('message', '')) > 100 else entry.get('message'),
                'trace_id': entry.get('trace_id')
            })
        return timeline[:20]  # Limit to first 20 entries
    
    def save_session(self):
        """Save the current session summary"""
        self.logger.save_session_summary(str(self.project_dir), self.system_prompt)


async def main():
    """Main entry point for the Claude Code Agent invoker"""
    
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is required")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python claude_code_agent.py <project_directory> <system_prompt_file> [task_prompt]")
        print("  python claude_code_agent.py <project_directory> <system_prompt_file> --rca <log_input>")
        print("  python claude_code_agent.py <project_directory> <system_prompt_file> --rca <log_input> <custom_prompt>")
        print("\nOptions:")
        print("  --rca: Perform Root Cause Analysis on logs")
        print("  <log_input>: Path to log file, directory, or direct log content")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    system_prompt_file = sys.argv[2]
    
    try:
        # Read system prompt from file
        with open(system_prompt_file, 'r') as f:
            system_prompt = f.read().strip()
        
        # Initialize the agent invoker
        invoker = ClaudeCodeAgentInvoker(project_dir, system_prompt)
        
        # Check if RCA mode
        if len(sys.argv) >= 4 and sys.argv[3] == '--rca':
            if len(sys.argv) < 5:
                print("Error: --rca requires log_input parameter")
                sys.exit(1)
            
            log_input = sys.argv[4]
            custom_prompt = sys.argv[5] if len(sys.argv) >= 6 else None
            
            print(f"Performing RCA on: {log_input}")
            results = await invoker.perform_rca(log_input, custom_prompt)
            
            # Print RCA summary
            print(f"\n{'='*60}")
            print("ROOT CAUSE ANALYSIS SUMMARY")
            print(f"{'='*60}")
            print(f"Success: {results['success']}")
            if 'log_analysis' in results:
                print(f"Total Errors: {results['log_analysis']['total_errors']}")
                print(f"Error Patterns: {results['log_analysis']['error_patterns']}")
                print(f"Affected Components: {results['log_analysis']['affected_components']}")
            if results['error']:
                print(f"Error: {results['error']}")
            print(f"{'='*60}")
            
        else:
            # Regular task execution
            task_prompt = sys.argv[3] if len(sys.argv) > 3 else None
            
            # Execute task or analyze project
            if task_prompt:
                results = await invoker.execute_task(task_prompt)
            else:
                results = await invoker.analyze_project()
            
            # Print results summary
            print(f"\n{'='*50}")
            print("EXECUTION SUMMARY")
            print(f"{'='*50}")
            print(f"Success: {results['success']}")
            print(f"Messages: {len(results['messages'])}")
            print(f"Tool calls: {len(results['tool_calls'])}")
            if results['error']:
                print(f"Error: {results['error']}")
            print(f"{'='*50}")
        
        # Save session
        invoker.save_session()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
