"""Lightweight HTTP API bridging UI <-> Ollama adapter <-> engine.

Endpoints (Flask):
- POST /api/prompt    -> { prompt, model? } -> runs adapter -> engine.handle_action
- POST /api/confirm   -> { actions: [...] } -> replays with confirm=True via handle_action(batch)
- POST /api/stt       -> multipart/form-data file=audio -> transcribes via whisper-cli if available
- GET  /health        -> health check

Notes:
- Keep deps minimal. Requires: flask (and optionally flask_cors for CORS).
- For Windows PowerShell: pip install flask flask-cors

Execution modes:
- Preferred:  python -m nova_ai.server   (runs as a package, relative imports work)
- Fallback:   python src\nova_ai\server.py  (we inject parent path so relative imports still resolve)
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import importlib
import pkgutil
import tempfile
from typing import Any, Dict

from flask import Flask, jsonify, request

try:
    from flask_cors import CORS  # type: ignore
    _HAS_CORS = True
except Exception:
    _HAS_CORS = False

try:
    if __package__ in (None, ""):
        # Script executed directly; ensure parent of this file is on sys.path
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))  # add src/nova_ai parent
        from nova_ai.core.engine import handle_action  # type: ignore
        from nova_ai.mcp.ollama_adapter import prompt_to_action, AdapterError  # type: ignore
    else:
        from .core.engine import handle_action
        from .mcp.ollama_adapter import prompt_to_action, AdapterError
except ImportError as _e:
    raise ImportError(f"Failed to import engine/adapter modules: {_e}")


def create_app() -> Flask:
    app = Flask(__name__)
    if _HAS_CORS:
        CORS(app)

    def _load_skills():
        """Dynamically import all modules in nova_ai.skills so they register skills."""
        try:
            import nova_ai.skills as skills_pkg  # type: ignore
            for _, name, _ in pkgutil.iter_modules(skills_pkg.__path__):
                importlib.import_module(f"nova_ai.skills.{name}")
        except Exception as e:
            # Do not crash server; return error info for diagnostics endpoint later.
            print(f"[nova_ai.server] Failed to load skills: {e}")

    _load_skills()

    @app.get("/api/skills")
    def api_skills():
        from .core.registry import list_skills
        return jsonify({"skills": sorted(list_skills().keys())})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/prompt")
    def api_prompt():
        try:
            data = request.get_json(force=True) or {}
        except Exception:
            return jsonify({"error": "invalid json"}), 400

        prompt = (data.get("prompt") or "").strip()
        model = (data.get("model") or os.environ.get("OLLAMA_MODEL") or "llama3.1:8b").strip()
        if not prompt:
            return jsonify({"error": "missing prompt"}), 400

        try:
            action = prompt_to_action(prompt, model=model, timeout=60)
        except AdapterError as e:
            return jsonify({"error": "adapter_error", "message": str(e)}), 502
        except Exception as e:
            return jsonify({"error": "server_error", "message": str(e)}), 500

        result = handle_action(action)
        return jsonify({"action": action, "result": result})

    @app.post("/api/confirm")
    def api_confirm():
        try:
            data = request.get_json(force=True) or {}
        except Exception:
            return jsonify({"error": "invalid json"}), 400

        actions = data.get("actions") or []
        if not isinstance(actions, list) or not actions:
            return jsonify({"error": "missing actions array"}), 400

        # Ensure confirm=True on all provided actions
        normalized = []
        for a in actions:
            if not isinstance(a, dict) or "action" not in a:
                continue
            args = dict(a.get("args") or {})
            args["confirm"] = True
            normalized.append({"action": a["action"], "args": args})

        result = handle_action({"action": "batch", "args": {"actions": normalized}})
        return jsonify(result)

    @app.post("/api/stt")
    def api_stt():
        """Transcribe audio via whisper CLI if available.

        Expects multipart/form-data with field 'audio'. Returns { text }.
        Configure executable via env WHISPER_CLI (default: 'whisper-cli').
        """
        if "audio" not in request.files:
            return jsonify({"error": "missing file field 'audio'"}), 400

        audio = request.files["audio"]
        whisper_exe = os.environ.get("WHISPER_CLI", "whisper-cli")
        model = os.environ.get("WHISPER_MODEL", "small")

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            audio.save(tmp)
            tmp_path = tmp.name

        # Run CLI
        try:
            # Example: whisper-cli audio.wav --model small --output - (stdout)
            # If the installed CLI doesn't support stdout, fallback to a temp transcript file.
            cmd = [whisper_exe, tmp_path, "--model", model, "--output", "-"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            if res.returncode == 0 and res.stdout.strip():
                text = res.stdout.strip()
                return jsonify({"text": text})

            # Fallback to a temp output file named .txt
            out_txt = tmp_path + ".txt"
            cmd2 = [whisper_exe, tmp_path, "--model", model, "--output", out_txt]
            res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res2.returncode == 0 and os.path.exists(out_txt):
                try:
                    with open(out_txt, "r", encoding="utf-8", errors="replace") as f:
                        return jsonify({"text": f.read().strip()})
                finally:
                    try:
                        os.remove(out_txt)
                    except Exception:
                        pass
            return jsonify({"error": "stt_failed", "stderr": (res.stderr or res2.stderr or "").strip()}), 502
        except FileNotFoundError:
            return jsonify({"error": "missing whisper-cli", "hint": "Set WHISPER_CLI env var or install whisper.cpp CLI"}), 501
        except Exception as e:
            return jsonify({"error": "stt_error", "message": str(e)}), 500
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("NOVA_PORT", "8000"))
    # Bind to 127.0.0.1 by default; Electron app can call http://localhost:8000
    app.run(host="127.0.0.1", port=port, debug=False)
