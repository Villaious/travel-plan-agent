from abc import ABC, abstractmethod
from typing import Any

from .message import Message
from travel_agent.tools.registry import ToolRegistry


class Agent(ABC):
    """Minimal agent base class inspired by the HelloAgents chapter template."""

    def __init__(self, name: str, system_prompt: str = "") -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.tools = ToolRegistry()
        self.history: list[Message] = []

    def add_tool(self, tool: Any) -> None:
        self.tools.register(tool)

    def get_history(self) -> list[Message]:
        return list(self.history)

    def remember_user_input(self, content: str) -> None:
        self.history.append(Message.user(content))

    def remember_answer(self, content: str) -> None:
        self.history.append(Message.assistant(content))

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
