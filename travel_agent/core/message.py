from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    role: str
    content: str
    created_at: datetime

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content, created_at=datetime.now())

    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role="assistant", content=content, created_at=datetime.now())
