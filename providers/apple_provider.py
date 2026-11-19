"""Apple Foundation Models provider (on-device, primary).

Runs the SDK's async API on a dedicated background event loop so Streamlit's
synchronous script runs can consume it as a plain iterator.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from typing import Iterator

import apple_fm_sdk as fm

from providers.base import Message, ProviderError, history_block

_loop: "_AsyncLoop | None" = None
_loop_lock = threading.Lock()


class _AsyncLoop:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def is_alive(self) -> bool:
        return self._thread.is_alive()


def _get_loop() -> _AsyncLoop:
    global _loop
    with _loop_lock:
        if _loop is None or not _loop.is_alive():
            _loop = _AsyncLoop()
        return _loop


async def _probe() -> tuple[bool, str | None]:
    model = fm.SystemLanguageModel()
    available, reason = model.is_available()
    return available, (reason.name if reason is not None else None)


def _compose_instructions(system_prompt: str, history: list[Message]) -> str | None:
    parts = [system_prompt.strip()] if system_prompt.strip() else []
    if history:
        parts.append("Conversation so far:\n" + history_block(history))
    return "\n\n".join(parts) or None


def _wrap_error(exc: Exception) -> ProviderError:
    name = type(exc).__name__
    if name == "ExceededContextWindowSizeError":
        return ProviderError(
            "Apple Foundation Models context window is full. "
            "Clear the conversation or continue with Ollama."
        )
    if name == "RateLimitedError":
        return ProviderError("Apple Foundation Models rate limited the request. Try again shortly.")
    if isinstance(exc, ProviderError):
        return exc
    return ProviderError(f"Apple Foundation Models error: {exc}")


class AppleProvider:
    label = "Apple Foundation Models"

    def __init__(
        self,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        history: list[Message] | None = None,
    ) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._closed = False
        self._loop = _get_loop()
        instructions = _compose_instructions(system_prompt, history or [])
        try:
            self._session = self._loop.run(self._create_session(instructions)).result()
        except Exception as exc:  # pragma: no cover - depends on host OS
            raise _wrap_error(exc) from exc

    async def _create_session(self, instructions: str | None):
        return fm.LanguageModelSession(instructions=instructions)

    @staticmethod
    def availability() -> tuple[bool, str | None]:
        try:
            return _get_loop().run(_probe()).result(timeout=10)
        except Exception as exc:
            return False, str(exc)

    def _options(self) -> fm.GenerationOptions:
        return fm.GenerationOptions(
            temperature=self.temperature,
            maximum_response_tokens=self.max_tokens,
        )

    def stream(self, messages: list[Message]) -> Iterator[str]:
        if self._closed:
            raise ProviderError("This Apple session is closed. Clear the conversation to restart.")
        if not messages:
            return
        prompt = messages[-1]["content"]
        snapshots: queue.Queue[tuple[str, object]] = queue.Queue()

        async def produce() -> None:
            try:
                options = self._options()
                async for snapshot in self._session.stream_response(prompt, options=options):
                    snapshots.put(("chunk", snapshot))
            except Exception as exc:
                snapshots.put(("error", exc))
            finally:
                snapshots.put(("done", None))

        future = self._loop.run(produce())
        previous = ""
        try:
            while True:
                try:
                    kind, payload = snapshots.get(timeout=0.2)
                except queue.Empty:
                    if future.done():
                        break
                    continue
                if kind == "done":
                    break
                if kind == "error":
                    raise _wrap_error(payload)  # type: ignore[arg-type]
                snapshot = str(payload)
                delta = snapshot[len(previous):] if snapshot.startswith(previous) else snapshot
                previous = snapshot
                if delta:
                    yield delta
        finally:
            if not future.done():
                future.cancel()

    def close(self) -> None:
        self._closed = True
        self._session = None
