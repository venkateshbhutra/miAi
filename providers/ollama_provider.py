"""Ollama provider (local, secondary / fallback)."""

from __future__ import annotations

from typing import Iterator

import ollama

from providers.base import Message, ProviderError, history_block


def list_models(host: str | None = None) -> list[str]:
    try:
        with ollama.Client(host=host) as client:
            return sorted(model.model for model in client.list().models if model.model)
    except Exception:
        return []


class OllamaProvider:
    label = "Ollama"

    def __init__(
        self,
        model: str,
        host: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_prompt: str = "",
        history: list[Message] | None = None,
    ) -> None:
        self.model = model
        self.host = host
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt.strip()
        self.history = history or []

    def _payload(self, messages: list[Message]) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        system = self.system_prompt
        if self.history:
            recap = history_block(self.history)
            system = f"{system}\n\nConversation so far:\n{recap}".strip()
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message["role"] in {"user", "assistant"}
        )
        return payload

    def stream(self, messages: list[Message]) -> Iterator[str]:
        options: dict[str, object] = {"temperature": self.temperature}
        if self.max_tokens:
            options["num_predict"] = self.max_tokens

        try:
            with ollama.Client(host=self.host) as client:
                for chunk in client.chat(
                    model=self.model,
                    messages=self._payload(messages),
                    stream=True,
                    options=options,
                ):
                    content = (chunk.message.content or "") if chunk.message else ""
                    if content:
                        yield content
        except Exception as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

    def close(self) -> None:
        return None
