# main.py
import importlib
import pkgutil
from core.engine import handle_command

def load_skills():
    """Auto-load all modules in the 'skills' folder."""
    import skills
    for _, name, _ in pkgutil.iter_modules(skills.__path__):
        importlib.import_module(f"skills.{name}")

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
