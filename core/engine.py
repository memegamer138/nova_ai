# core/engine.py
from core.registry import get_skill, required_permissions
import re
import os
from typing import Optional, Tuple, Dict


def _extract_filename(command: str) -> Optional[str]:
    """Try several strategies to find a filename in the command.

    Priority:
      1. phrase after 'named' or 'called' (strong signal)
      2. token with a file-like extension (e.g. notes.txt)
      3. token after the verb (create/delete) if it looks reasonable
    """
    # 1) 'named' or 'called' (stop if a destination phrase follows)
    m = re.search(r"\b(?:named|called)\s+([^,;]+)", command)
    if m:
        val = m.group(1).strip(' .!,')
        # if the captured value contains a destination marker like ' in ' or ' to ', drop tail
        val = re.split(r"\b(?:in|to|on)\b", val, maxsplit=1)[0].strip()
        return val

    # 2) token with extension
    m = re.search(r"\b([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b", command)
    if m:
        return m.group(1)

    # 3) token immediately after the verb
    m = re.search(r"\b(?:create|delete)\s+(?:a\s+)?(?:file\s+)?([^\s,]+)", command)
    if m:
        token = m.group(1).strip(' .!,')
        # avoid returning the generic word 'file' or common stopwords
        if token.lower() not in ("file", "a", "the", "named", "called", "in", "my"):
            return token

    return None


def _extract_destination(command: str) -> Optional[str]:
    """Try to extract a destination directory from the command.

    Returns an absolute path or None. Supports:
      - absolute paths (Windows C:\... or Unix /...)
      - named folders like Desktop, Downloads, Documents, Pictures, OneDrive, Home
      - short phrases: 'in my desktop folder', 'in Downloads', 'to Documents'
    """
    # 1) absolute Windows path (e.g. C:\Users\...)
    m = re.search(r"[A-Za-z]:\\[^,;]+", command)
    if m:
        return os.path.expandvars(os.path.expanduser(m.group(0).strip()))

    # 2) absolute Unix-like path
    m = re.search(r"(/[^,;]+)", command)
    if m and m.group(1).startswith("/"):
        return os.path.expandvars(os.path.expanduser(m.group(1).strip()))

    # 3) named folder mapping
    name_map = {
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "onedrive": os.path.join(os.path.expanduser("~"), "OneDrive"),
        "home": os.path.expanduser("~"),
    }

    # look for patterns like 'in my desktop folder' or 'in Downloads'
    m = re.search(r"\b(?:in|to|on)\s+(?:my\s+)?([A-Za-z0-9_\- ]+)(?:\s+folder|\s+directory)?\b", command)
    if m:
        key = m.group(1).strip().lower()
        # if the key contains multiple words, take last token (e.g., 'my desktop folder')
        key_token = key.split()[-1]
        if key_token in name_map:
            return name_map[key_token]

    # 4) explicit folder mentioned like 'Downloads' anywhere
    for token, path in name_map.items():
        if re.search(rf"\b{re.escape(token)}\b", command, flags=re.IGNORECASE):
            return path

    return None


def parse_command(command: str) -> Tuple[Optional[str], Dict[str, str]]:
    """Improved intent parser that extracts intent and parameters.

    Returns (intent_name, params) or (None, {}).
    """
    text = command.lower()

    # If both verbs present it's ambiguous
    has_create = "create" in text
    has_delete = "delete" in text
    if has_create and has_delete:
        return None, {}

    filename = _extract_filename(command)
    dest = _extract_destination(command)

    # If destination is an absolute path that contains a filename (e.g. /tmp/x.txt or C:\a\b.txt),
    # treat that as the filename (if not already extracted) and set dest to its directory.
    if dest and os.path.isabs(dest):
        base = os.path.basename(dest)
        if base and ('.' in base or (filename and filename.endswith(base))):
            # set filename to the basename if we don't already have a clean filename
            if not filename or filename == dest:
                filename = base
            dest = os.path.dirname(dest) or dest

    if has_create:
        return "create_file", {"filename": filename or "newfile.txt", "dest": dest}
    if has_delete:
        return "delete_file", {"filename": filename or "unknown.txt", "dest": dest}

    return None, {}


def handle_command(command: str, granted_permissions=None):
    """Handle a natural-language command.

    granted_permissions: optional iterable of permission strings that the caller has granted.
    If omitted, treated as an empty set (no permissions).
    """
    intent, params = parse_command(command)
    if not intent:
        return "Sorry, I didn't understand that command."

    # permissions check
    req_perms = required_permissions(intent)
    granted = set(granted_permissions) if granted_permissions else set()
    if req_perms and not req_perms.issubset(granted):
        return f"Permission denied for intent '{intent}'. Required: {sorted(req_perms)}"

    skill_func = get_skill(intent)
    if not skill_func:
        return f"No skill found for intent '{intent}'."

    try:
        result = skill_func(**params)
        return result
    except Exception as e:
        return f"Error: {e}"
