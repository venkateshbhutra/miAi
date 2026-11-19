# MiAi

## What it is

A Streamlit-based AI chat UI built primarily on Apple Foundation Models (on-device), with Ollama (local) as fallback. It runs as a locally hosted chatbot: prompts stay on the device (Apple) or on localhost (Ollama), with no cloud API involved. This project also serves as a portfolio of AI skills built by working on harnessing RAG, MCP, skills, and other relevant tools (in progress).

## Requirements

- Python 3.13 (venv is 3.13.13).
- `streamlit>=1.40` (1.67.0 installed), `ollama>=0.6`, `python-dotenv>=1.0`.
- `apple-fm-sdk>=0.2.2`, installed only on macOS (`sys_platform == "darwin"`); needs macOS 26+ with Apple Intelligence enabled in System Settings.
- Ollama server running, with a model pulled. Development machine: M1, 16 GB unified memory, macOS 27.2.1 — so 4-bit 4B–8B models fit; 4B is faster.

## Setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
ollama serve            # if not already running
ollama pull llama3.1:8b # the default in .env.example
.venv/bin/streamlit run app.py
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `MIAI_DEFAULT_PROVIDER` | `apple` | `apple` or `ollama`; anything else falls back to `apple` |
| `MIAI_DEFAULT_MODEL` | `llama3.1:8b` | Ollama model (legacy alias `MIAI_OLLAMA_MODEL` also read) |
| `MIAI_SYSTEM_PROMPT` | `You are MiAi, a concise and helpful assistant.` | Prepended system instructions |
| `MIAI_TEMPERATURE` | `0.7` | 0.0–1.0 sampling randomness |
| `MIAI_MAX_TOKENS` | unset → model default | `0` also means model default (`app.py:201`) |
| `MIAI_AUTO_FALLBACK` | `true` | Fall back to Ollama if Apple fails before the first token |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address (not `MIAI_`-prefixed) |

Settings load once at import (`config.py:10`), so restart Streamlit after editing `.env`. Sidebar widgets override `.env` per session; `.env` only sets the initial values.

## Known limits

- No automated tests yet.
- Non-macOS: `providers/__init__.py:1` imports `AppleProvider` unconditionally, which imports `apple_fm_sdk` at module top, so the whole app fails to import even though the SDK is darwin-only in `requirements.txt`.
- macOS 26+ is required for `apple-fm-sdk` / Apple Intelligence.
- Fallback is not per-token: if Apple emits any text and then errors, the error surfaces instead of switching (`app.py:100-116`).
- `list_models()` returns `[]` on any failure (`ollama_provider.py:12-17`), so "server down" and "no models" look identical in the UI.
- Switching provider/model/prompt/temperature rebuilds and closes the cached provider; conversation history is re-sent as a text recap, so Apple's internal session state and the recap can drift.

## Roadmap

Planned: RAG, MCP tools, guardrails (in progress).
