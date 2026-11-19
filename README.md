1. What it is about?
     A Streamlit based AI chat UI based primarily on Apple Foundation Models on-device with Ollama local as fallback. This serves as locally hosted chatbot which offers privacy of data. This project will also serves as a portfolio of AI skills build by working on harnessing, RAGS, MCPs, Skills and other relevant tools.
2. Requirements:
     Python 3.13, macOS 26+ with Apple Intelligence for the Apple path, Ollama installed with a model pulled (preferably one supported by your configuration. (4B-8B parameterized models for faster response on Apple M1 series laptop).
3. Setup
    python3.13 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cp .env.example .env
4. Run
    ollama serve            # if not already running
    ollama pull llama3.1:8b # the default in .env.example
    .venv/bin/streamlit run app.py
5. Configuration:
    A short table of the MIAI_* vars + OLLAMA_HOST, and the one non-obvious rule: MIAI_MAX_TOKENS=0 means "model default".
6. Known limits:
    The entire project is build on a macbook with M1 processor. Hence, Apple path requires macOS 26+; on non-macOS the app can't import because providers/__init__.py imports the Apple SDK unconditionally; Ollama unreachable looks the same as "no models" in the UI. Also the foundational model offered by Apple should be available for activating the project.