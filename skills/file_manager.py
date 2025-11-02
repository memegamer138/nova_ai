# skills/file_manager.py
import os
import shutil
import logging
from core.registry import register_skill

# Configure basic logging for this skill
logger = logging.getLogger("file_manager")
if not logger.handlers:
    handler = logging.FileHandler("logs/file_manager.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Base fallback paths
BASE_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
if not os.path.isdir(BASE_PATH):
    BASE_PATH = os.path.expanduser("~")

# Named folders mapping
NAMED_FOLDERS = {
    "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "documents": os.path.join(os.path.expanduser("~"), "Documents"),
    "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
    "onedrive": os.path.join(os.path.expanduser("~"), "OneDrive"),
    "home": os.path.expanduser("~"),
}


def _resolve_path(dest, name=None):
    """Resolve destination folder, with optional filename appended."""
    base_dir = BASE_PATH

    if dest:
        candidate = os.path.expanduser(os.path.expandvars(dest)).strip()
        candidate_lower = candidate.lower()
        if candidate_lower in NAMED_FOLDERS:
            base_dir = NAMED_FOLDERS[candidate_lower]
        elif os.path.isabs(candidate):
            base_dir = candidate
        else:
            maybe = os.path.join(BASE_PATH, candidate)
            if os.path.isdir(maybe):
                base_dir = maybe
            else:
                base_dir = os.path.join(BASE_PATH, candidate)

    if name:
        return os.path.join(base_dir, name)
    return base_dir


# -------------------- FILE OPERATIONS -------------------- #

@register_skill("create_file")
def create_file(filename, content="", dest=None):
    filename = (filename or "newfile.txt").strip(' "\'')
    path = _resolve_path(dest, filename)

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
        msg = f"File '{filename}' created in {os.path.dirname(path)}."
        logger.info(msg)
        return {"status": "success", "path": path, "message": msg}
    except Exception as e:
        msg = f"Error creating file '{filename}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("delete_file")
def delete_file(filename, dest=None):
    filename = (filename or "").strip(' "\'')
    path = _resolve_path(dest, filename)

    if not os.path.exists(path):
        msg = f"'{filename}' not found in {os.path.dirname(path)}."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        os.remove(path)
        msg = f"Deleted '{filename}'."
        logger.info(msg)
        return {"status": "success", "path": path, "message": msg}
    except Exception as e:
        msg = f"Error deleting '{filename}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("read_file")
def read_file(filename, dest=None):
    filename = (filename or "").strip(' "\'')
    path = _resolve_path(dest, filename)

    if not os.path.exists(path):
        msg = f"'{filename}' not found."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read file '{filename}'")
        return {"status": "success", "path": path, "content": content}
    except Exception as e:
        msg = f"Error reading '{filename}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("write_file")
def write_file(filename, dest=None, content="", append=False):
    filename = (filename or "").strip(' "\'')
    path = _resolve_path(dest, filename)

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content or "")
        msg = f"File '{filename}' written {'(appended)' if append else '(overwritten)'} in {os.path.dirname(path)}."
        logger.info(msg)
        return {"status": "success", "path": path, "message": msg}
    except Exception as e:
        msg = f"Error writing to '{filename}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("move_file")
def move_file(src, dest, src_from=None):
    # resolve source path: if src_from provided, use it as the base folder
    if src_from:
        src_path = _resolve_path(src_from, src)
    else:
        src_path = _resolve_path(None, src)
    dest_path = _resolve_path(dest, os.path.basename(src))

    if not os.path.exists(src_path):
        msg = f"Source file '{src}' not found."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(src_path, dest_path)
        msg = f"Moved '{src}' to '{dest_path}'."
        logger.info(msg)
        return {"status": "success", "src": src_path, "dest": dest_path, "message": msg}
    except Exception as e:
        msg = f"Error moving '{src}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("copy_file")
def copy_file(src, dest, src_from=None):
    if src_from:
        src_path = _resolve_path(src_from, src)
    else:
        src_path = _resolve_path(None, src)
    dest_path = _resolve_path(dest, os.path.basename(src))

    if not os.path.exists(src_path):
        msg = f"Source file '{src}' not found."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(src_path, dest_path)
        msg = f"Copied '{src}' to '{dest_path}'."
        logger.info(msg)
        return {"status": "success", "src": src_path, "dest": dest_path, "message": msg}
    except Exception as e:
        msg = f"Error copying '{src}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


# -------------------- FOLDER OPERATIONS -------------------- #

@register_skill("create_folder")
def create_folder(foldername, dest=None):
    foldername = (foldername or "NewFolder").strip(' "\'')
    path = _resolve_path(dest, foldername)

    try:
        os.makedirs(path, exist_ok=True)
        msg = f"Folder '{foldername}' created in {os.path.dirname(path)}."
        logger.info(msg)
        return {"status": "success", "path": path, "message": msg}
    except Exception as e:
        msg = f"Error creating folder '{foldername}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("delete_folder")
def delete_folder(foldername, dest=None, recursive=False):
    foldername = (foldername or "").strip(' "\'')
    path = _resolve_path(dest, foldername)

    if not os.path.exists(path):
        msg = f"Folder '{foldername}' not found."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        if recursive:
            shutil.rmtree(path)
        else:
            os.rmdir(path)
        msg = f"Folder '{foldername}' deleted."
        logger.info(msg)
        return {"status": "success", "path": path, "message": msg}
    except Exception as e:
        msg = f"Error deleting folder '{foldername}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}


@register_skill("list_dir")
def list_dir(path=None):
    dir_path = _resolve_path(path) if path else BASE_PATH
    if not os.path.exists(dir_path):
        msg = f"Directory '{dir_path}' not found."
        logger.warning(msg)
        return {"status": "error", "message": msg}

    try:
        items = os.listdir(dir_path)
        msg = f"Contents of '{dir_path}': {items}"
        logger.info(msg)
        return {"status": "success", "path": dir_path, "contents": items, "message": msg}
    except Exception as e:
        msg = f"Error listing directory '{dir_path}': {e}"
        logger.error(msg)
        return {"status": "error", "message": msg}
