# src/nova_ai/mcp/ollama_adapter.py
import json
import shlex
import subprocess
from typing import Optional, Dict, Any

class AdapterError(RuntimeError):
    pass

ALLOWED_ACTIONS = {"create_file","delete_file","create_folder","delete_folder","move_file","copy_file","read_file","write_file","list_dir"}

def _run_ollama_cli(prompt: str, model: str = "llama3.1:8b", timeout: int = 30) -> str:
    # Use the CLI; ensure we pass a system prompt asking for JSON only
    # Primary invocation (some versions accept --prompt)
    cmd = ["ollama", "run", model, "--prompt", prompt]
    try:
        # enforce UTF-8 decoding and replace invalid bytes to avoid UnicodeDecodeError on Windows
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except FileNotFoundError as e:
        raise AdapterError("ollama CLI not found on PATH") from e

    if res.returncode == 0:
        return res.stdout

    # If the CLI rejects the --prompt flag, try passing the prompt via stdin as a fallback.
    stderr = (res.stderr or "").lower()
    if "unknown flag" in stderr or "flag provided but not defined" in stderr or "unknown shorthand flag" in stderr:
        try:
            res2 = subprocess.run(["ollama", "run", model], input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        except FileNotFoundError as e:
            raise AdapterError("ollama CLI not found on PATH") from e
        if res2.returncode == 0:
            return res2.stdout
        raise AdapterError(f"ollama CLI failed (stdin fallback): {res2.stderr.strip()}")

    # Otherwise, propagate the original error
    raise AdapterError(f"ollama CLI failed: {res.stderr.strip()}")

def parse_and_validate(raw: str) -> Dict[str,Any]:
    # Try to extract a JSON object from raw text (strip surrounding markdown or code fences)
    def _extract_first_json(s: str) -> str:
        """Find and return the first balanced JSON object in s.
        Uses a simple state machine to ignore braces inside strings.
        Returns the JSON substring or raises ValueError if not found.
        """
        s = s.replace("```json", "").replace("```", "")  # remove common code fences
        start = s.find("{")
        if start == -1:
            raise ValueError("no JSON object start found")

        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(s)):
            ch = s[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        raise ValueError("no balanced JSON object found")

    forbidden_paths = ["C:\\Windows", "/etc", "/bin", "/usr", "System32"]

    # Attempt extraction and parsing. Support multiple top-level JSON objects (some models emit several)
    def _extract_all_json(s: str) -> list:
        out = []
        i = 0
        s = s.strip()
        while True:
            try:
                jstr = _extract_first_json(s[i:])
            except ValueError:
                break
            # find absolute indices to advance
            start = s.find(jstr, i)
            if start == -1:
                break
            end = start + len(jstr)
            out.append(jstr)
            i = end
            if i >= len(s):
                break
        return out

    json_strs = _extract_all_json(raw)
    if not json_strs:
        # fallback: try to parse any JSON-looking lines
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        for line in lines:
            try:
                obj = json.loads(line)
                json_strs = [line]
                break
            except Exception:
                try:
                    j = _extract_first_json(line)
                    obj = json.loads(j)
                    json_strs = [j]
                    break
                except Exception:
                    continue
        if not json_strs:
            raise AdapterError(f"failed to parse JSON from model output; raw start: {raw[:200]!r}")

    objs = []
    for j in json_strs:
        try:
            objs.append(json.loads(j))
        except Exception:
            # skip unparsable fragments
            continue

    if not objs:
        raise AdapterError(f"failed to parse JSON from model output; raw start: {raw[:200]!r}")

    # If multiple objects, return a batch action containing them
    if len(objs) > 1:
        # validate inner objects minimally
        for o in objs:
            act = o.get("action")
            if act not in ALLOWED_ACTIONS and act != "none":
                raise AdapterError(f"unknown or disallowed action in batch: {act}")
            if not isinstance(o.get("args", {}), dict):
                raise AdapterError("args must be an object in batch")
        return {"action": "batch", "args": {"actions": objs}}

    obj = objs[0]
    action = obj.get("action")
    args = obj.get("args", {})

    # Basic forbidden-path check (after we have args)
    for key in ("filename", "dest"):
        val = args.get(key, "") if isinstance(args, dict) else ""
        if val and any(p.lower() in val.lower() for p in forbidden_paths):
            raise AdapterError(f"forbidden path detected in {key}: {val}")
    if action not in ALLOWED_ACTIONS:
        raise AdapterError(f"unknown or disallowed action: {action}")
    if not isinstance(args, dict):
        raise AdapterError("args must be an object")
    # additional validation/sanitization here (filenames, dest)
    return {"action": action, "args": args}

def prompt_to_action(prompt: str, model: str = "llama3.1:8b", timeout: int = 30) -> Dict[str,Any]:
    system_prompt = (
       "You are a tool that must output a single JSON object and nothing else. "
       "The JSON must be {\"action\": <action-string>, \"args\": {...}}. "
       "Allowed actions: create_file, delete_file, create_folder, delete_folder, move_file, copy_file, read_file, write_file, list_dir. "
       "For example: {\"action\":\"create_file\",\"args\":{\"filename\":\"notes.txt\",\"dest\":\"~/Desktop/Projects\",\"content\":\"\"}}"
    )
    full = system_prompt + "\n\nUser: " + prompt
    raw = _run_ollama_cli(full, model=model, timeout=timeout)
    return parse_and_validate(raw)