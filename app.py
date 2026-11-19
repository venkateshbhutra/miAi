"""MiAi - a minimal Streamlit chatbot with Apple Foundation Models (primary)
and Ollama (local fallback)."""

from __future__ import annotations

from typing import Iterator

import streamlit as st

from config import Settings, load_settings
from providers import (
    AppleProvider,
    Message,
    OllamaProvider,
    ProviderError,
    list_models,
)

st.set_page_config(page_title="MiAi", page_icon="💬", layout="centered")

PROVIDER_LABELS = {
    "apple": "Apple Foundation Models (on-device)",
    "ollama": "Ollama (local)",
}


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("apple_status", None)


@st.cache_data(ttl=15, show_spinner=False)
def available_models(host: str) -> list[str]:
    return list_models(host)


def apple_available() -> tuple[bool, str | None]:
    if st.session_state.apple_status is None:
        st.session_state.apple_status = AppleProvider.availability()
    return st.session_state.apple_status


def cached_apple(
    settings: Settings,
    system_prompt: str,
    temperature: float,
    max_tokens: int | None,
    history: list[Message],
) -> AppleProvider:
    signature = ("apple", system_prompt, round(temperature, 2), max_tokens)
    cached = st.session_state.get("_apple_provider")
    if cached and cached["signature"] == signature:
        return cached["provider"]
    if cached:
        cached["provider"].close()
    provider = AppleProvider(
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        history=history,
    )
    st.session_state["_apple_provider"] = {"signature": signature, "provider": provider}
    return provider


def cached_ollama(
    settings: Settings,
    model: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int | None,
    history: list[Message],
) -> OllamaProvider:
    signature = ("ollama", model, settings.ollama_host, system_prompt, round(temperature, 2), max_tokens)
    cached = st.session_state.get("_ollama_provider")
    if cached and cached["signature"] == signature:
        return cached["provider"]
    if cached:
        cached["provider"].close()
    provider = OllamaProvider(
        model=model,
        host=settings.ollama_host,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        history=history,
    )
    st.session_state["_ollama_provider"] = {"signature": signature, "provider": provider}
    return provider


def reset_conversation() -> None:
    st.session_state.messages = []
    for key in ("_apple_provider", "_ollama_provider"):
        cached = st.session_state.pop(key, None)
        if cached:
            cached["provider"].close()


def stream_with_fallback(
    primary,
    fallback,
    messages: list[Message],
    notes: list[str],
) -> Iterator[str]:
    produced = False
    try:
        for chunk in primary.stream(messages):
            produced = True
            yield chunk
        return
    except Exception as exc:
        if fallback is None or produced:
            raise
        notes.append(f"{primary.label} unavailable ({exc}). Falling back to {fallback.label}.")
    yield from fallback.stream(messages)


def render_answer(provider, fallback, notes: list[str]) -> tuple[str, Exception | None]:
    placeholder = st.empty()
    text = ""
    error: Exception | None = None
    try:
        for delta in stream_with_fallback(
            provider, fallback, st.session_state.messages, notes
        ):
            text += delta
            placeholder.markdown(text + "▌")
    except Exception as exc:
        error = exc
    placeholder.markdown(text or "_No response._")
    return text, error


def main() -> None:
    init_state()
    settings = load_settings()

    st.title("💬 MiAi")
    st.caption("Private, on-device chat: Apple Foundation Models first, Ollama as fallback.")

    with st.sidebar:
        st.header("Settings")
        provider = st.radio(
            "Primary provider",
            options=list(PROVIDER_LABELS),
            format_func=lambda key: PROVIDER_LABELS[key],
            index=list(PROVIDER_LABELS).index(settings.provider),
        )
        auto_fallback = st.checkbox("Fall back to Ollama on failure", value=settings.auto_fallback)

        models = available_models(settings.ollama_host)
        default_model = settings.default_model
        if models:
            index = models.index(default_model) if default_model in models else 0
            ollama_model = st.selectbox("Ollama model", models, index=index)
        else:
            ollama_model = st.text_input(
                "Ollama model",
                value=default_model,
                help="Ollama is not reachable or has no models. `ollama pull <model>` first.",
            )

        system_prompt = st.text_area("System prompt", value=settings.system_prompt, height=120)
        temperature = st.slider("Temperature", 0.0, 1.0, float(settings.temperature), 0.05)
        max_tokens = st.number_input(
            "Max response tokens (0 = model default)",
            min_value=0,
            max_value=8192,
            value=int(settings.max_tokens or 0),
            step=64,
        )

        st.divider()
        available, reason = apple_available()
        if available:
            st.success("Apple Foundation Models: ready")
        else:
            st.warning(f"Apple Foundation Models unavailable: {reason or 'unknown reason'}")
        if models:
            st.success(f"Ollama: {len(models)} model(s) available")
        else:
            st.warning("Ollama: not reachable or no models")

        if st.button("Clear conversation", use_container_width=True):
            reset_conversation()
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask MiAi anything...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    token_limit = int(max_tokens) or None
    history = st.session_state.messages[:-1]
    notes: list[str] = []

    apple_provider = None
    ollama_provider = None
    try:
        ollama_provider = cached_ollama(
            settings, ollama_model, system_prompt, temperature, token_limit, history
        )
    except Exception as exc:
        notes.append(f"Could not prepare Ollama: {exc}")

    if provider == "apple":
        if not available:
            notes.append(f"Apple unavailable: {reason or 'unknown reason'}.")
            if not auto_fallback:
                st.error(notes[-1])
                return
            if ollama_provider is None:
                st.error("No provider available. Start Ollama or enable Apple Intelligence.")
                return
            active, fallback = ollama_provider, None
        else:
            try:
                apple_provider = cached_apple(
                    settings, system_prompt, temperature, token_limit, history
                )
            except ProviderError as exc:
                notes.append(str(exc))
                if not auto_fallback:
                    st.error(str(exc))
                    return
                active, fallback = ollama_provider, None
            else:
                active = apple_provider
                fallback = ollama_provider if auto_fallback else None
    else:
        active = ollama_provider
        fallback = None
        if active is None:
            st.error("Ollama is not available. Start it with `ollama serve` and pull a model.")
            return

    if active is None:
        st.error("No provider available.")
        return

    with st.chat_message("assistant"):
        text, error = render_answer(active, fallback, notes)

    for note in notes:
        st.caption(note)

    if error is not None:
        st.error(str(error) or type(error).__name__)
        if active is apple_provider:
            active.close()
            st.session_state.pop("_apple_provider", None)
    if text:
        st.session_state.messages.append({"role": "assistant", "content": text})


if __name__ == "__main__":
    main()
