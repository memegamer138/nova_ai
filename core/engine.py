# core/engine.py
from core.registry import get_skill
import re

def parse_command(command: str):
    """Very simple intent parser."""
    command = command.lower()
    if "create" in command and "file" in command:
        # Extract filename after 'named' or 'called' if present
        match = re.search(r"(?:named|called)?\s*([a-zA-Z0-9_\-\.]+)", command)
        filename = match.group(1) if match else "newfile.txt"
        return "create_file", {"filename": filename}
    elif "delete" in command and "file" in command:
        match = re.search(r"(?:named|called)?\s*([a-zA-Z0-9_\-\.]+)", command)
        filename = match.group(1) if match else "unknown.txt"
        return "delete_file", {"filename": filename}
    else:
        return None, {}

def handle_command(command: str):
    intent, params = parse_command(command)
    if not intent:
        return "Sorry, I didn't understand that command."

    skill_func = get_skill(intent)
    if not skill_func:
        return f"No skill found for intent '{intent}'."

    try:
        result = skill_func(**params)
        return result
    except Exception as e:
        return f"Error: {e}"
