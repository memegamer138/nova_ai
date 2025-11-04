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

## Usage

Start the agent from the repository root:

```powershell
C:/path/to/python.exe main.py
```

Try natural commands at the prompt:

- create a file called notes.txt in my desktop folder
- create file named groceries.txt in OneDrive
- create report.md in Downloads
- delete file named notes.txt in Documents

The parser supports named folders (Desktop, Downloads, Documents, Pictures, OneDrive) and absolute paths. If a command is ambiguous (contains both "create" and "delete"), the agent will refuse to act to avoid accidental operations.

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

