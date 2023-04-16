import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any


@dataclass
class RequestSchema:
    headers: dict[str, Any]
    data: dict[str, Any]
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class User:
    login: str
    password: str
    last_message: Optional["Message"] = None


@dataclass
class Message:
    user: User
    text: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class Chat:
    name: str
    members: list[User] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
