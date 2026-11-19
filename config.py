"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class Settings:
    default_provider: str = "apple"
    default_model: str = "llama3.1:8b"
    system_prompt: str = "You are MiAi, a concise and helpful assistant."
    temperature: float = 0.7
    max_tokens: int | None = None
    auto_fallback: bool = True
    ollama_host: str = "http://localhost:11434"

    @property
    def provider(self) -> str:
        return "ollama" if self.default_provider == "ollama" else "apple"


def load_settings() -> Settings:
    provider = os.getenv("MIAI_DEFAULT_PROVIDER", "apple").strip().lower()
    return Settings(
        default_provider=provider if provider in {"apple", "ollama"} else "apple",
        default_model=os.getenv("MIAI_DEFAULT_MODEL", "").strip()
        or os.getenv("MIAI_OLLAMA_MODEL", "").strip()
        or "llama3.1:8b",
        system_prompt=os.getenv("MIAI_SYSTEM_PROMPT", "").strip()
        or "You are MiAi, a concise and helpful assistant.",
        temperature=_get_float("MIAI_TEMPERATURE", 0.7),
        max_tokens=_get_int("MIAI_MAX_TOKENS"),
        auto_fallback=_get_bool("MIAI_AUTO_FALLBACK", True),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
        or "http://localhost:11434",
    )
