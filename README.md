## Nova AI — Local MCP-style Assistant (Project Vision)

Nova AI is an experimental, local-first AI agent platform (an "MCP") that can interact with your PC and perform useful tasks on your behalf. The goal is to build a collaborative assistant that can go beyond simple scripted actions and help with creative work, research, development, and desktop automation — similar in spirit to fictional assistants like "Jarvis", but intentionally scoped for a personal development sandbox.

This repository contains an early MVP: a minimal core that routes natural-language intents to pluggable "skills" (Python modules). Current sample skills let the agent create and delete files on your machine. The design prioritizes simplicity so you can extend it quickly with new capabilities.

## Key goals and constraints

- Local-first: actions run on your machine. No cloud access is required by default.
- Extensible: skills are simple Python modules that register intents. Add new skills to make the agent do more.
- Safe by default: destructive actions should require clear intent (and can be extended with confirmation prompts or permission gating).
- Not a commercial product (for now): this is a personal project and learning playground.

## What this MVP can do now

- Parse simple text commands and map them to intents (create/delete file).
- Create files in common folders (Desktop, Downloads, Documents, OneDrive) or arbitrary absolute paths.
- Delete files from supported folders.

## Architecture overview

- main.py — CLI runner and skill loader. Auto-imports `skills.*` modules and runs a simple REPL.
- core/engine.py — intent parsing and dispatch. Converts natural-language commands into (intent, params) and calls the registered skill.
- core/registry.py — skill registry and decorators. Skills register themselves with intent names.
- skills/ — folder where individual skill modules live (for example `skills/file_manager.py`).
- config/settings.json — optional configuration for defaults (not heavily used by the MVP yet).

## How to add a new skill

1. Create a new Python module in `skills/`, e.g. `skills/browser.py`.
2. Use the `@register_skill("intent_name")` decorator from `core.registry`.
3. Implement the function signature expected by your intent (kwargs from `engine.parse_command` will be passed through).

Example:

```python
from core.registry import register_skill

@register_skill('open_url')
def open_url(url):
	# implementation that opens a browser
	pass
```

4. Restart the app (or dynamically reload modules) and call the intent.

## Security, privacy & safety

This project runs code on your local machine. That means you are responsible for what skills do. A few recommendations:

- Treat untrusted skill code like any untrusted code. Don't run modules you don't review.
- Add explicit confirmation prompts for destructive actions (deleting files, modifying system settings).
- Consider a permission layer that limits which folders or commands skills can access.
- Log actions and provide an audit view so you can review what the agent did.

## Development notes

- The parser is intentionally simple and heuristic-based. For more robust intent parsing, consider integrating an NLP model or rule engine.
- The code is Python 3.12+ (as used during development). Keep dependencies minimal; the core uses only the Python stdlib.

## Desktop UI (Electron)

This project includes a lightweight Electron-based desktop UI under `ui/desktop` that loads `index.html` and communicates with the Flask server at `http://127.0.0.1:8000`.

How it works:
- The Electron main process (`ui/desktop/main.js`) opens a BrowserWindow and loads `index.html`.
- `preload.js` exposes a small API on `window.nova` which POSTs to the backend endpoints `/api/prompt` and `/api/confirm`.
- The backend (Flask) must be running for the UI to function.

Quick start (Windows PowerShell):

```powershell
# from repo root
# create venv (if needed) and install Python deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# start the server (preferred from src so relative imports work)
Set-Location src
python -m nova_ai.server

# in a second terminal: start the Electron UI
Set-Location ui\desktop
npm install
npm run start
```

Convenience script:
- There's a helper `run_desktop.ps1` at the repository root that will create a venv (if missing), install Python requirements, start the Flask server in a new PowerShell window, and launch the Electron UI. Run it from PowerShell:

```powershell
.\run_desktop.ps1
```

Packaging:
- To produce a distributable standalone app, use an Electron packager/builder (for example `electron-builder` or `electron-packager`) inside `ui/desktop` and bundle or include the Python runtime and server invocation. Packaging Python+Electron is a larger topic; I can add a basic `electron-builder` config if you want.

---

## About this README

This README has been updated to reflect the current code in the repository (CLI, Flask backend, and Electron desktop UI). It contains:
- A concise overview of what the project currently does
- Step-by-step installation and run instructions (Windows PowerShell)
- How the desktop UI interacts with the backend
- How to install and troubleshoot the Ollama CLI (optional LLM runtime)
- Suggestions for packaging and next steps / roadmap

If anything in your local setup differs (Python path, Node version, Windows vs WSL), adapt the commands accordingly.

**Important:** The project currently supports a built-in regex-based parser (fast, local) and an optional Ollama CLI adapter for LLM-driven reasoning. If the Ollama binary is not on your PATH, the server will fall back to the regex parser so the UI remains functional.

---

## Quick Installation & Run (Windows PowerShell)

Prerequisites:
- Python 3.11+ (3.12 recommended)
- Node.js + npm (for Electron UI)
- Optional: Ollama CLI (if you want LLM reasoning; otherwise the regex fallback will be used)

1) Create and activate a Python virtual environment, then install Python deps:

```powershell
# From the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Start the backend server (preferred run as package from `src`):

```powershell
Set-Location src
python -m nova_ai.server
# The server binds to 127.0.0.1:8000 by default; change port with $env:NOVA_PORT
```

3) Start the desktop Electron UI (new terminal):

```powershell
Set-Location ui\desktop
npm install
npm run start
```

**Alternate:** Convenience helper
- You can use the included helper `run_desktop.ps1` from the repo root. It will create a venv (if missing), install Python deps, start the Flask server in a new PowerShell window, and launch the Electron UI:

```powershell
.\run_desktop.ps1
```

---

## Ollama CLI (recommended) — install and verify

The repository includes an optional adapter (`src/nova_ai/mcp/ollama_adapter.py`) that calls the external `ollama` CLI. If you want LLM-powered reasoning instead of the regex parser, install Ollama and pull a model.
To experience the full functionality of the app, please install ollama from the official webiste.
Installation (Windows):
- Download and run the Windows installer from https://ollama.com (preferred), OR
- Use Winget if available:

```powershell
winget install Ollama.Ollama
```

Verification (in PowerShell):

```powershell
Get-Command ollama
ollama --version
where.exe ollama
```

Pull the `llama3.1:8b` model:

```powershell
ollama pull llama3.1:8b
```

If `ollama` is installed but the server still can't find it, ensure the terminal you use to run the Flask server inherits PATH that includes the `ollama` binary and restart the terminal after installation.

Environment variable controls:
- `OLLAMA_MODEL` — model name used by the adapter (default in code: `llama3.1:8b`)
- `NOVA_PORT` — port the Flask server binds to (default 8000)

Example (set model in the current PowerShell session):

```powershell
$env:OLLAMA_MODEL = 'llama3.1:8b'
```

**Note:** A `.env` file is not required by the current code; the adapter reads environment variables via `os.environ`. If you prefer a `.env` workflow, load it before starting the server or add a small loader (python-dotenv) to the server entry.


## Development & Extending

- Add new skills in `src/nova_ai/skills/` and register them via `@register_skill(...)` in `core/registry.py`.
- The engine exposes two code paths:
   - `handle_command()` — fast regex-based parser (no external LLM needed)
   - `prompt_to_action()` via the Ollama adapter — LLM-driven intent parsing
- To change adapters or add a different provider (OpenAI, local llama.cpp wrapper), implement a new adapter module under `src/nova_ai/mcp/` and update the server to call it.

Packaging ideas
- To ship a standalone desktop app that includes the Python backend, use an Electron packager and include a launcher that starts the Python server in the app bundle. Tools to investigate: `electron-builder`, `electron-forge`, `pyinstaller` (to bundle Python into an executable), or `briefcase`.

---

## Roadmap / Next steps

- Packaging: Add a basic `electron-builder` configuration and a small wrapper to start the bundled Python server.
- Adapter flexibility: Add a configuration option to switch adapters (ollama/openai/llama.cpp) at runtime.
- Permission gating: Add user confirmation/permission model for risky operations and a persistent audit log UI.
- Tests & CI: Add automated tests for the Flask API and the UI flows (integration test harness).

---

## Contributing

- PRs welcome. Please run tests (when added) and follow the repository coding conventions.

## License

If you want to publish this project publicly, add a license file (e.g., MIT or Apache-2.0). No license is included yet.


# What talks to what

```
USER (voice/text)
   ↓
INPUT LAYER (wake-word / speech2text or CLI)
   ↓
LLM (reasoner)  ←→ Tool spec (what skills exist, with schemas)
   ↓ (JSON: intent(s) + params)
VALIDATION LAYER (safety checks, sandboxing, confirmations)
   ↓
DISPATCHER / EXECUTOR  (calls registered skill functions)
   ↓
FILE_MANAGER SKILL (creates/deletes/moves/copies/etc.)
   ↓
AUDIT LOG + TTS / text response back to user
```

## License

This repository does not yet include a formal license file. If you want to collaborate publicly, consider adding an OSS license (MIT, Apache-2.0, etc.).

---

