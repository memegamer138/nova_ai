# main.py
import importlib
import pkgutil
from nova_ai.core.engine import handle_command
import os
# TODO: Check move commands from non desktop location
# Ensure logs folder exists
if not os.path.isdir('logs'):
    os.makedirs('logs')

def load_skills():
    """Auto-load all modules in the 'skills' folder."""
    import nova_ai.skills as skills_pkg
    for _, name, _ in pkgutil.iter_modules(skills_pkg.__path__):
        importlib.import_module(f"nova_ai.skills.{name}")

def main():
    print("Nova AI — MVP Active. Type 'exit' to quit.")
    load_skills()

    while True:
        command = input("\n> ").strip()
        if command.lower() in ["exit", "quit"]:
            print("Cya chump.")
            break

        response = handle_command(command)
        print(response)

if __name__ == "__main__":
    main()
