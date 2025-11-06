# src/nova_ai/mcp/ollama_adapter.py
import json
import shlex
import subprocess
from typing import Optional, Dict, Any, List
import os

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

    def _normalize_content(val: Any) -> str:
        """Normalize content to a string.
        - list/tuple -> join with newlines
        - dict with keys like line1,line2 -> join values ordered by the number
        - other dict -> JSON dump
        - non-string -> str()
        """
        if isinstance(val, (list, tuple)):
            return "\n".join(str(x) for x in val)
        if isinstance(val, dict):
            # If keys look like line\d+, order by number
            keys = list(val.keys())
            if keys and all(isinstance(k, str) and k.lower().startswith("line") for k in keys):
                def _keynum(k: str) -> int:
                    try:
                        return int("".join(ch for ch in k if ch.isdigit()) or 0)
                    except Exception:
                        return 0
                ordered = [val[k] for k in sorted(keys, key=_keynum)]
                return "\n".join(str(x) for x in ordered)
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return str(val)
        if isinstance(val, str):
            return val
        return str(val)

    def _split_file_path(path: str) -> tuple[Optional[str], str]:
        if not path:
            return None, ""
        p = os.path.normpath(path)
        directory, name = os.path.split(p)
        if directory in ("", "."):
            return None, name
        return directory, name

    def _normalize_args(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(args or {})
        # Common synonyms
        if action in {"create_folder", "delete_folder"}:
            # accept folder_name, name, folder, filename (LLM confusion) -> foldername
            for k in ("folder_name", "name", "folder", "filename"):
                if k in args and "foldername" not in args:
                    args["foldername"] = args.pop(k)
                    break
            # accept dest synonyms
            for k in ("path", "directory", "dir", "location"):
                if k in args and "dest" not in args:
                    args["dest"] = args.pop(k)
                    break

        elif action in {"create_file", "write_file", "read_file", "delete_file"}:
            # filename synonyms
            for k in ("name", "file", "basename"):
                if k in args and "filename" not in args:
                    args["filename"] = args.pop(k)
                    break
            # path handling: file_path/filepath/path may contain both
            for k in ("file_path", "filepath", "path"):
                if k in args:
                    maybe_path = args.pop(k)
                    if isinstance(maybe_path, str):
                        d, n = _split_file_path(maybe_path)
                        if n and "filename" not in args:
                            args["filename"] = n
                        if d and "dest" not in args:
                            args["dest"] = d
                    break
            # dest synonyms
            for k in ("folder", "directory", "dir", "location"):
                if k in args and "dest" not in args:
                    args["dest"] = args.pop(k)
                    break
            # content normalization for create/write_file
            if action in {"create_file", "write_file"}:
                if "content" not in args:
                    # derive from 'lines' or 'text' or 'body' or 'data'
                    for k in ("lines", "text", "body", "data"):
                        if k in args:
                            args["content"] = _normalize_content(args.pop(k))
                            break
                else:
                    # if content is not a string, normalize
                    if not isinstance(args["content"], str):
                        args["content"] = _normalize_content(args["content"])

        elif action in {"move_file", "copy_file"}:
            # src synonyms
            for k in ("source", "file", "name"):
                if k in args and "src" not in args:
                    args["src"] = args.pop(k)
                    break
            # If src given as path, split
            if "src" in args and isinstance(args["src"], str) and ("/" in args["src"] or "\\" in args["src"]):
                d, n = _split_file_path(args["src"])
                if n:
                    args["src"] = n
                if d and "src_from" not in args:
                    args["src_from"] = d
            # dest synonyms
            for k in ("destination", "folder", "directory", "dir", "location"):
                if k in args and "dest" not in args:
                    args["dest"] = args.pop(k)
                    break

        elif action == "list_dir":
            # accept folder/directory/dir/location/dest
            for k in ("folder", "directory", "dir", "location", "dest"):
                if k in args and "path" not in args:
                    args["path"] = args.pop(k)
                    break

        return args

    # If multiple objects, normalize each and return a batch
    # If multiple objects, return a batch action containing them
    if len(objs) > 1:
        norm_actions: List[Dict[str, Any]] = []
        for o in objs:
            act = o.get("action")
            if act not in ALLOWED_ACTIONS and act != "none":
                raise AdapterError(f"unknown or disallowed action in batch: {act}")
            if not isinstance(o.get("args", {}), dict):
                raise AdapterError("args must be an object in batch")
            o["args"] = _normalize_args(act, o.get("args", {}))
            norm_actions.append(o)
        return {"action": "batch", "args": {"actions": norm_actions}}

    obj = objs[0]
    action = obj.get("action")
    args = _normalize_args(action, obj.get("args", {}))

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