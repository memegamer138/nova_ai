# skills/file_manager.py
import os
from core.registry import register_skill

# Default to the user's Desktop, fall back to home if Desktop doesn't exist
BASE_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
if not os.path.isdir(BASE_PATH):
    BASE_PATH = os.path.expanduser("~")


@register_skill("create_file")
def create_file(filename, content="", dest=None):
    # sanitize filename and build path
    filename = filename or "newfile.txt"
    filename = filename.strip(' "\'')
    # resolve destination: if dest is provided and is an absolute path or existing folder, use it
    base_dir = BASE_PATH
    if dest:
        # expand user vars and normalize
        candidate = os.path.expanduser(os.path.expandvars(dest))
        if os.path.isabs(candidate):
            base_dir = candidate
        else:
            # if candidate exists as a folder relative to home, prefer that
            maybe = os.path.join(os.path.expanduser("~"), candidate)
            if os.path.isdir(maybe):
                base_dir = maybe
            else:
                # fallback: try joining candidate to BASE_PATH
                base_dir = os.path.join(BASE_PATH, candidate)

    path = os.path.join(base_dir, filename)

    # ensure directory exists if filename contains subdir
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.isdir(dirpath):
        try:
            os.makedirs(dirpath, exist_ok=True)
        except Exception:
            return f"Error: cannot create directory for '{filename}'."

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        return f"File '{filename}' created in {base_dir}."
    except Exception as e:
        return f"Error creating file '{filename}': {e}"


@register_skill("delete_file")
def delete_file(filename, dest=None):
    filename = filename or ""
    filename = filename.strip(' "\'')
    base_dir = BASE_PATH
    if dest:
        candidate = os.path.expanduser(os.path.expandvars(dest))
        if os.path.isabs(candidate):
            base_dir = candidate
        else:
            maybe = os.path.join(os.path.expanduser("~"), candidate)
            if os.path.isdir(maybe):
                base_dir = maybe
            else:
                base_dir = os.path.join(BASE_PATH, candidate)

    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            return f"Deleted '{filename}'."
        except Exception as e:
            return f"Error deleting '{filename}': {e}"
    else:
        return f"'{filename}' not found in {base_dir}."
