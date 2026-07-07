class AgentError(Exception):
    """Base exception for agent failures."""


class ToolError(AgentError):
    """Raised when a tool cannot complete its task."""
