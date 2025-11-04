# core/engine.py
from .registry import get_skill, required_permissions
import re
import os
from typing import Optional, Tuple, Dict
import logging
import uuid
import time

# ensure logs directory exists (placed at repo root /logs)
repo_root = os.path.dirname(os.path.dirname(__file__))
logs_dir = os.path.join(repo_root, "logs")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "nova_engine.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    logger = logging.getLogger(__name__)

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
