# core/engine.py
from .registry import get_skill, required_permissions
import re
import os
from typing import Optional, Tuple, Dict
import logging
from logging.handlers import RotatingFileHandler
import uuid
import time

# Ensure logs directory (at current working directory) exists
logs_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Set up module logger with rotation (avoid global basicConfig)
LOGGER = logging.getLogger("nova_engine")
if not LOGGER.handlers:
    handler = RotatingFileHandler(os.path.join(logs_dir, "nova_engine.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)

# -------------------- COMMAND PARSING -------------------- #

def _extract_target_name(command: str) -> Optional[str]:
    """
    Extract file or folder name from command.
    Priority:
      1. phrase after 'named' or 'called'
      2. token with extension (for files)
      3. token immediately after verbs (create/delete/move/copy)
    """
    # 'named' or 'called'
    m = re.search(r"\b(?:named|called)\s+([^,;]+)", command)
    if m:
        val = m.group(1).strip(' .!,')
        val = re.split(r"\b(?:in|to|on)\b", val, maxsplit=1)[0].strip()
        return val

    # token with file extension
    m = re.search(r"\b([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b", command)
    if m:
        return m.group(1)

    # token after verbs
    m = re.search(r"\b(?:create|delete|move|copy|read|write)\s+(?:a\s+)?(?:file|folder\s+)?([^\s,]+)", command)
    if m:
        token = m.group(1).strip(' .!,')
        if token.lower() not in ("file", "folder", "a", "the", "named", "called", "in", "my"):
            return token
    return None


def _extract_destination(command: str) -> Optional[str]:
    """Extract destination directory from command.

    Notes:
    - Prefer named folders (Desktop, OneDrive, etc.).
    - Support patterns like 'OneDrive/Code' or 'OneDrive\\Code' where a named folder
      is followed by a subpath.
    - Fall back to absolute Windows (C:\...) and absolute Unix (/...) paths.
    """
    # named folders mapping
    name_map = {
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "onedrive": os.path.join(os.path.expanduser("~"), "OneDrive"),
        "home": os.path.expanduser("~"),
    }

    # 1) named folder with subpath, e.g. 'OneDrive/Code' or 'OneDrive\\Code'
    m = re.search(r"\b(Desktop|Downloads|Documents|Pictures|OneDrive|Home)\s*[\\/]\s*([^,;\n]+)", command, flags=re.IGNORECASE)
    if m:
        key = m.group(1).strip().lower()
        sub = m.group(2).strip().strip('/\\')
        base = name_map.get(key)
        if base:
            return os.path.join(base, sub)

    # 2) explicit phrasing like 'in OneDrive' or 'in my Documents'
    m = re.search(r"\b(?:in|to|on)\s+(?:my\s+)?([A-Za-z0-9_\- ]+)(?:\s+folder|\s+directory)?\b", command)
    if m:
        key = m.group(1).strip().lower()
        key_token = key.split()[-1]
        if key_token in name_map:
            return name_map[key_token]

    # 3) absolute Windows path (e.g. C:\Users\...)
    m = re.search(r"[A-Za-z]:\\[^,;]+", command)
    if m:
        return os.path.expandvars(os.path.expanduser(m.group(0).strip()))

    # 4) absolute Unix-like path (/some/path)
    m = re.search(r"(/[^,;]+)", command)
    if m and m.group(1).startswith("/"):
        return os.path.expandvars(os.path.expanduser(m.group(1).strip()))

    # 5) fallback: any named folder mentioned anywhere
    for token, path in name_map.items():
        if re.search(rf"\b{re.escape(token)}\b", command, flags=re.IGNORECASE):
            return path

    return None


def _extract_content(command: str) -> Optional[str]:
    """
    Extract content from command for write/append operations.
    Looks for patterns like:
    - 'write "Hello world" to file.txt'
    - 'append "Hello"'
    """
    m = re.search(r'"([^"]+)"', command)
    if m:
        return m.group(1)
    return None


def parse_command(command: str) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Map natural language to intents and parameters.
    Supports:
    - File: create/delete/read/write/move/copy
    - Folder: create/delete/list
    """
    text = command.lower()

    # simple ambiguity guard: if both create and delete appear, refuse to parse
    if "create" in text and "delete" in text:
        return None, {}
    params = {}

    # Detect intents
    if "create" in text and "folder" in text:
        intent = "create_folder"
        params["foldername"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
    elif "delete" in text and "folder" in text:
        intent = "delete_folder"
        params["foldername"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
        params["recursive"] = "recursive" in text
    elif "list" in text or "show contents" in text:
        intent = "list_dir"
        params["path"] = _extract_destination(command)
    elif "create" in text or "make" in text:
        intent = "create_file"
        params["filename"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
    elif "delete" in text:
        intent = "delete_file"
        params["filename"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
    elif "read" in text:
        intent = "read_file"
        params["filename"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
    elif "write" in text or "append" in text:
        intent = "write_file"
        params["filename"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
        params["content"] = _extract_content(command)
        params["append"] = "append" in text
    elif "move" in text:
        intent = "move_file"
        # src should be the target name (file) and dest is the destination folder/path
        params["src"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
        # support 'from <location>' to specify source folder
        m_from = re.search(r"\bfrom\s+(?:my\s+)?([A-Za-z0-9_\- ]+)\b", command, flags=re.IGNORECASE)
        if m_from:
            params["src_from"] = m_from.group(1).strip()
    elif "copy" in text:
        intent = "copy_file"
        params["src"] = _extract_target_name(command)
        params["dest"] = _extract_destination(command)
        m_from = re.search(r"\bfrom\s+(?:my\s+)?([A-Za-z0-9_\- ]+)\b", command, flags=re.IGNORECASE)
        if m_from:
            params["src_from"] = m_from.group(1).strip()
    else:
        return None, {}

    return intent, params


# -------------------- COMMAND HANDLING -------------------- #

def handle_command(command: str, granted_permissions=None):
    """Handle a natural-language command."""
    cid = uuid.uuid4().hex
    raw_cmd = (command or "").strip()
    short_cmd = (raw_cmd[:500] + "...") if len(raw_cmd) > 500 else raw_cmd
    logger = LOGGER

    logger.info("cmd.received cid=%s command=%s", cid, short_cmd)

    intent, params = parse_command(command)
    if not intent:
        logger.info("cmd.parsed cid=%s result=%s", cid, "no-intent")
        return "Sorry, I didn't understand that command."

    # permissions check
    req_perms = required_permissions(intent)
    granted = set(granted_permissions) if granted_permissions else set()
    if req_perms and not req_perms.issubset(granted):
        logger.info("cmd.permission_denied cid=%s intent=%s req_perms=%s granted=%s", cid, intent, sorted(req_perms), sorted(granted))
        return f"Permission denied for intent '{intent}'. Required: {sorted(req_perms)}"

    skill_func = get_skill(intent)
    if not skill_func:
        logger.info("cmd.no_skill cid=%s intent=%s", cid, intent)
        return f"No skill found for intent '{intent}'."

    try:
        param_summary = {k: (v if isinstance(v, (str, int, float)) else str(type(v))) for k, v in (params or {}).items()}
    except Exception:
        param_summary = {}
    logger.info("cmd.parsed cid=%s intent=%s params=%s", cid, intent, param_summary)

    # execute skill and time it
    start = time.time()
    try:
        result = skill_func(**params)
        duration_ms = int((time.time() - start) * 1000)
        # result summary
        try:
            res_summary = str(result)
        except Exception:
            res_summary = "<unserializable result>"
        if len(res_summary) > 200:
            res_summary = res_summary[:200] + "..."
        logger.info("cmd.finished cid=%s intent=%s duration_ms=%d result=%s", cid, intent, duration_ms, res_summary)
        return result
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.exception("cmd.error cid=%s intent=%s duration_ms=%d error=%s", cid, intent, duration_ms, e)
        return f"Error: {e}"


def handle_action(action: dict, granted_permissions=None):
    """Handle a structured action (from an LLM adapter or other source).

    Accepts either a single action dict {"action": <str>, "args": {...}}
    or a batch action {"action":"batch","args":{"actions":[...]}}.

    Safety behavior:
    - If an action is considered destructive (delete_file, delete_folder, move_file, write_file)
      and the action's args do not include `'confirm': True`, the engine returns a
      requires-confirmation response instead of executing.
    - Permissions are enforced using the registry.required_permissions() helper.

    Returns:
    - For a single executed action: the skill's return value.
    - For a batch where all actions executed: {"status":"batch","results": [..]}.
    - If confirmation required: {"status":"requires_confirmation","pending": [...]}.
    - On error: {"status":"error","message": ...}
    """
    cid = uuid.uuid4().hex
    logger = LOGGER
    logger.info("action.received cid=%s action=%s", cid, action)

    if not isinstance(action, dict) or "action" not in action:
        logger.warning("action.invalid cid=%s action=%r", cid, action)
        return {"status": "error", "message": "invalid action format"}

    granted = set(granted_permissions) if granted_permissions else set()

    # normalize to list of actions
    actions = []
    if action.get("action") == "batch":
        args = action.get("args", {}) or {}
        actions = args.get("actions", []) if isinstance(args, dict) else []
    else:
        actions = [action]

    # helpers
    destructive = {"delete_file", "delete_folder", "move_file", "write_file"}
    pending_confirm = []
    results = []

    from .registry import required_permissions, get_skill

    for idx, act in enumerate(actions):
        if not isinstance(act, dict):
            pending_confirm.append({"index": idx, "reason": "malformed action"})
            continue
        intent = act.get("action")
        args = act.get("args") or {}

        # basic validation
        if not intent or not isinstance(args, dict):
            pending_confirm.append({"index": idx, "reason": "invalid intent or args"})
            continue

        # permission check
        req_perms = required_permissions(intent)
        if req_perms and not req_perms.issubset(granted):
            logger.info("action.permission_denied cid=%s intent=%s req=%s granted=%s", cid, intent, sorted(req_perms), sorted(granted))
            return {"status": "error", "message": f"permission denied for intent '{intent}'"}

        # confirmation check for destructive actions
        if intent in destructive:
            if not args.get("confirm"):
                # collect pending confirmation; include the original args for transparency
                pending_confirm.append({"index": idx, "action": intent, "args": args})
                continue

        # dispatch
        skill = get_skill(intent)
        if not skill:
            logger.warning("action.no_skill cid=%s intent=%s", cid, intent)
            results.append({"status": "error", "message": f"no skill for intent '{intent}'"})
            continue

        # remove control args (like confirm) before calling the skill
        call_args = {k: v for k, v in args.items() if k != "confirm"}

        try:
            start = time.time()
            res = skill(**call_args)
            duration_ms = int((time.time() - start) * 1000)
            results.append(res)
            logger.info("action.executed cid=%s intent=%s duration_ms=%d result=%s", cid, intent, duration_ms, str(res)[:200])
        except Exception as e:
            logger.exception("action.error cid=%s intent=%s error=%s", cid, intent, e)
            results.append({"status": "error", "message": str(e)})

    if pending_confirm:
        logger.info("action.requires_confirmation cid=%s pending=%s", cid, pending_confirm)
        return {"status": "requires_confirmation", "pending": pending_confirm}

    if len(results) == 1 and action.get("action") != "batch":
        return results[0]

    return {"status": "batch", "results": results}
