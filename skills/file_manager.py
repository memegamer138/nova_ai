# skills/file_manager.py
import os
from core.registry import register_skill

BASE_PATH = os.path.expanduser("~/OneDrive")  # customize path

@register_skill("create_file")
def create_file(filename, content=""):
    path = os.path.join(BASE_PATH, filename)
    with open(path, "w") as f:
        f.write(content)
    return f"File '{filename}' created in OneDrive."

@register_skill("delete_file")
def delete_file(filename):
    path = os.path.join(BASE_PATH, filename)
    if os.path.exists(path):
        os.remove(path)
        return f"Deleted '{filename}'."
    else:
        return f"'{filename}' not found."
