"""
Morphic Agents Module

A comprehensive module for orchestrating Claude Code Agents with concurrent execution,
result aggregation, and sophisticated workflow management.
"""

from .agent_orchestrator import AgentOrchestrator, AgentTask, AgentResult
from .claude_code_agent import ClaudeCodeAgentInvoker
from .workflows import RCAWorkflow, CodeReviewWorkflow, SecurityAnalysisWorkflow
from .result_processor import ResultProcessor, ResultAggregator
from .exceptions import AgentError, OrchestratorError, WorkflowError

__version__ = "1.0.0"
__all__ = [
    "AgentOrchestrator",
    "AgentTask", 
    "AgentResult",
    "ClaudeCodeAgentInvoker",
    "RCAWorkflow",
    "CodeReviewWorkflow", 
    "SecurityAnalysisWorkflow",
    "ResultProcessor",
    "ResultAggregator",
    "AgentError",
    "OrchestratorError", 
    "WorkflowError"
]
