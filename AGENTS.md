# AGENTS.md

## Working mode: coach, not coder

Venky is the PO, PL, and developer here; he is learning AI engineering. Act as a coach and guide:

- Do not write or edit code unless he explicitly asks for that change.
- Explain the why, show the smallest next step, and let him type it.
- Point at exact files/lines to read, name the concept, then wait.
- No unexplained code dumps; teach one concept at a time.

Default answer shape: what this piece does, why it matters for the product, what to try next.

## What this is

Small Streamlit chat app: Apple Foundation Models (on-device, primary) with Ollama as local fallback. No README, no tests, no CI, no git repo, no linter/typecheck config. Nothing here enforces style; keep files small and commented only where intent is non-obvious.

## Commands

Use the existing venv; Python 3.13 is installed at `.venv`.

```bash
.venv/bin/streamlit run app.py      # run the app (http://localhost:8501)
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m compileall -q app.py config.py providers   # syntax check only
.venv/bin/python -c "import app"    # import smoke test (prints harmless ScriptRunContext warning)
```

There is no test suite, so verification means: compile/import check, then exercise the UI with a real provider.

Setup: `cp .env.example .env` (settings are env vars, loaded once via `load_dotenv()` in `config.py:10`).

## Architecture

- `app.py` — entire UI plus orchestration. Single `main()`; Streamlit reruns the whole script per interaction.
- `config.py` — frozen `Settings` dataclass; env prefix `MIAI_*` plus `OLLAMA_HOST`. `Settings.provider` normalizes to `"apple"`/`"ollama"`.
- `providers/base.py` — `Message` TypedDict, `ChatProvider` Protocol (`stream()` + `close()`), `ProviderError`, and `history_block()` (flattens prior turns to text).
- `providers/apple_provider.py` — Apple SDK is async; it is bridged to a sync iterator via one dedicated background event loop thread (`_get_loop`), with a queue feeding `stream()`.
- `providers/ollama_provider.py` — `list_models()` returns `[]` on any failure instead of raising; chat streams via a `with ollama.Client(...)` context manager.
- `providers/__init__.py` re-exports the public surface; import from `providers`, not submodules.

## Non-obvious behavior you must not break

- Apple-first fallback is sequential, not per-token: `stream_with_fallback` (`app.py:100`) only falls back if the primary raises before emitting anything. Once text is produced, the error propagates.
- Providers are cached in `st.session_state` keyed by a settings signature (`cached_apple`/`cached_ollama`). Changing model, prompt, temperature, or history rebuilds and `close()`s the old one. Preserve that close-on-replace pattern to avoid leaked Apple sessions.
- History is passed as a text recap, not as message objects, to Apple (`_compose_instructions`) and Ollama (`_payload`); `app.py:202` sends `messages[:-1]` as history and the newest turn separately. Apple's `LanguageModelSession` also holds its own state, so do not "fix" this by replaying the full transcript.
- `max_tokens=0` in `.env` means "model default": `_get_int` yields `0`, and `app.py:201` converts falsy to `None`.
- Apple errors are normalized to friendly `ProviderError`s by type name (`_wrap_error`). Adding new SDK errors should follow that pattern rather than leaking raw exceptions to the UI.

## Platform gotchas

- `providers/__init__.py` imports `AppleProvider` unconditionally, which imports `apple_fm_sdk` at module top. On non-macOS the package fails to import even though `requirements.txt` only installs the SDK on `sys_platform == "darwin"`. Apple path also needs macOS 26+ with Apple Intelligence enabled.
- Ollama needs a running server (`ollama serve`) and a pulled model; `list_models` swallowing errors means "no models" and "server down" look identical in the UI.
- `.venv/`, `__pycache__/`, `.env`, and `.streamlit/secrets.toml` are gitignored; never commit secrets.
