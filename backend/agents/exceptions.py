"""
Custom exceptions for the Morphic Agents module
"""


class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass


class OrchestratorError(AgentError):
    """Exception raised by the agent orchestrator"""
    pass


class WorkflowError(AgentError):
    """Exception raised during workflow execution"""
    pass


class ConfigurationError(AgentError):
    """Exception raised for configuration issues"""
    pass


class RateLimitError(AgentError):
    """Exception raised when rate limits are exceeded"""
    pass


class AuthenticationError(AgentError):
    """Exception raised for authentication failures"""
    pass


class ValidationError(AgentError):
    """Exception raised for input validation failures"""
    pass
