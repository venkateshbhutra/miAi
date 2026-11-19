"""Shared provider types and helpers."""

from __future__ import annotations

from typing import Iterator, Protocol, TypedDict


class Message(TypedDict):
    role: str
    content: str


class ProviderError(RuntimeError):
    """Raised when a chat provider cannot fulfil a request."""


class ChatProvider(Protocol):
    label: str

    def stream(self, messages: list[Message]) -> Iterator[str]:
        """Yield response text deltas for the given conversation."""
        ...

    def close(self) -> None:
        """Release any resources held by the provider."""
        ...


def history_block(messages: list[Message], limit: int = 8, max_chars: int = 2000) -> str:
    """Render recent turns as plain text so a fresh session can pick up context."""
    recent = messages[-limit:]
    lines: list[str] = []
    for message in recent:
        role = "User" if message["role"] == "user" else "Assistant"
        content = " ".join(message["content"].split())
        if len(content) > max_chars // max(len(recent), 1):
            content = content[: max_chars // max(len(recent), 1)] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines[-limit:])
