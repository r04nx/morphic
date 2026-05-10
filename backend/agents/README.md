# Claude Code Agent Invoker

A Python script to invoke Claude Code agents with GitHub MCP server integration and comprehensive logging.

## Features

- **Directory-based project analysis**: Analyze any codebase directory
- **Custom system prompts**: Provide custom instructions for the agent
- **GitHub MCP server integration**: Extended capabilities with GitHub tools
- **Comprehensive logging**: Detailed session logs and summaries
- **Agent event tracking**: Track all messages, tool calls, and file modifications

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
export GITHUB_PERSONAL_ACCESS_TOKEN='your-github-token'  # Optional, for GitHub MCP features
```

## Usage

### Basic Usage

```bash
python claude_code_agent.py <project_directory> <system_prompt_file>
```

### With Custom Task

```bash
python claude_code_agent.py <project_directory> <system_prompt_file> "Analyze the security vulnerabilities in this codebase"
```

### Root Cause Analysis (RCA) Mode

```bash
# RCA with log file
python claude_code_agent.py <project_directory> <system_prompt_file> --rca /path/to/logs.txt

# RCA with log directory
python claude_code_agent.py <project_directory> <system_prompt_file> --rca /path/to/logs/

# RCA with direct log content
python claude_code_agent.py <project_directory> <system_prompt_file> --rca "ERROR: Payment failed..."

# RCA with custom prompt
python claude_code_agent.py <project_directory> <system_prompt_file> --rca /path/to/logs.txt "Focus on payment processing issues"
```

### Examples

#### 1. Project Analysis
```bash
python claude_code_agent.py /path/to/project system_prompt.txt
```

#### 2. Bug Fixing
```bash
python claude_code_agent.py /path/to/project bug_fix_prompt.txt "Fix the memory leak in the authentication module"
```

#### 3. Code Review
```bash
python claude_code_agent.py /path/to/project code_review_prompt.txt "Review the recent changes and suggest improvements"
```

#### 4. SRE Incident Response
```bash
python claude_code_agent.py /path/to/project sre_system_prompt.txt --rca /var/log/application.log "Investigate payment processing failures"
```

#### 5. Production Log Analysis
```bash
python claude_code_agent.py /path/to/project sre_system_prompt.txt --rca sample_logs.txt
```

## System Prompt File Format

Create a text file with your system prompt. Example:

```
You are an expert Python developer specializing in security and performance optimization.
Focus on identifying potential vulnerabilities, memory leaks, and inefficient code patterns.
Provide actionable recommendations with code examples when applicable.
```

## Logging

The script creates comprehensive logs in the `agent_logs` directory:

- `agent_session_YYYYMMDD_HHMMSS.log`: Detailed execution logs
- `session_summary_YYYYMMDD_HHMMSS.json`: Structured session data including:
  - Messages exchanged
  - Tool calls made
  - Files modified
  - Errors encountered
  - Timing information

## Configuration Options

The agent can be customized by modifying the `create_agent_options` method:

- `permission_mode`: Control how the agent executes tools
- `allowed_tools`: Specify which tools Claude can access
- `mcp_servers`: Add additional MCP servers for extended functionality

## Error Handling

The script includes comprehensive error handling:
- Validates project directory existence
- Checks for required environment variables
- Logs all errors with context
- Provides graceful failure modes

## Integration with Morphic

This agent invoker can be integrated into the Morphic incident response system:
- Use for automated code analysis during incident triage
- Generate fixes for detected issues
- Create GitHub PRs automatically
- Track all agent activities for audit purposes
