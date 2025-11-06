"""Nova AI CLI

Default: Use the Ollama LLM adapter to translate prompts into actions, then
dispatch via engine.handle_action(). If the adapter is unavailable or returns
an error, fall back to the regex-based handle_command() parser.

Special commands:
- Type ':help' for help
- Type ':mode regex' to force regex-only mode (toggle)
- Type ':mode llm' to force LLM-first mode (toggle)
"""

import importlib
import pkgutil
import os
import logging
from logging.handlers import RotatingFileHandler
from nova_ai.core.engine import handle_command, handle_action
from nova_ai.mcp.ollama_adapter import prompt_to_action, AdapterError

# Ensure logs folder exists
if not os.path.isdir('logs'):
    os.makedirs('logs')

# CLI logger
CLI_LOGGER = logging.getLogger("nova_cli")
if not CLI_LOGGER.handlers:
    _h = RotatingFileHandler(os.path.join('logs', 'cli.log'), maxBytes=500_000, backupCount=2, encoding='utf-8')
    _f = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    _h.setFormatter(_f)
    CLI_LOGGER.addHandler(_h)
    CLI_LOGGER.setLevel(logging.INFO)


def load_skills():
    """Auto-load all modules in the 'skills' folder."""
    import nova_ai.skills as skills_pkg
    for _, name, _ in pkgutil.iter_modules(skills_pkg.__path__):
        importlib.import_module(f"nova_ai.skills.{name}")


def _print_help():
    print("""
Commands:
  - Enter a natural language command; by default it will be sent to the LLM.
  - If the LLM is unavailable, the engine falls back to regex parsing.
  - Destructive actions will ask for confirmation before execution.

Special:
  :help           Show this help
  :mode llm       Prefer LLM adapter first (default)
  :mode regex     Use regex parser only (no LLM)
  exit | quit     Exit the program
""".strip())


def _confirm_and_execute_pending(pending_list):
    """Ask the user for confirmation and execute pending destructive actions.

    pending_list is a list of dicts with keys like {index, action, args}.
    """
    if not pending_list:
        print("No actions pending confirmation.")
        return

    # Summarize actions
    print("The following actions require confirmation:")
    for i, item in enumerate(pending_list, 1):
        act = item.get("action") or item.get("reason")
        args = item.get("args") or {}
        print(f"  {i}. {act} {args}")

    ans = input("Proceed? (y/N): ").strip().lower()
    if ans != 'y':
        print("Cancelled.")
        return

    # Build a batch with confirm=True for actionable entries
    actions = []
    for item in pending_list:
        if not item.get("action"):
            continue
        args = dict(item.get("args") or {})
        args["confirm"] = True
        actions.append({"action": item["action"], "args": args})
    if not actions:
        print("Nothing to execute.")
        return

    result = handle_action({"action": "batch", "args": {"actions": actions}})
    print(result)


def main():
    print("Nova AI — LLM-first CLI. Type ':help' for help; 'exit' to quit.")
    load_skills()

    # Modes: 'llm' (default) or 'regex'
    mode = 'llm'
    model = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')

    while True:
        command = input("\n> ").strip()
        if not command:
            continue
        low = command.lower()
        if low in ["exit", "quit"]:
            print("Cya chump.")
            break
        if low == ":help":
            _print_help()
            continue
        if low.startswith(":mode"):
            parts = low.split()
            if len(parts) == 2 and parts[1] in ("llm", "regex"):
                mode = parts[1]
                print(f"Mode set to: {mode}")
                CLI_LOGGER.info("mode.changed mode=%s", mode)
            else:
                print("Usage: :mode llm | :mode regex")
            continue

        # Regex-only mode
        if mode == 'regex':
            CLI_LOGGER.info("command.regex input=%s", command)
            response = handle_command(command)
            CLI_LOGGER.info("command.regex result=%s", str(response)[:300])
            print(response)
            continue

        # LLM-first mode (default): try adapter, then fallback to regex
        try:
            CLI_LOGGER.info("command.llm input=%s model=%s", command, model)
            action = prompt_to_action(command, model=model, timeout=60)
            CLI_LOGGER.info("command.llm action=%s", action)
            result = handle_action(action)
            if isinstance(result, dict) and result.get("status") == "requires_confirmation":
                CLI_LOGGER.info("command.llm requires_confirmation pending=%s", result.get("pending"))
                _confirm_and_execute_pending(result.get("pending") or [])
            else:
                CLI_LOGGER.info("command.llm result=%s", str(result)[:300])
                print(result)
        except AdapterError as e:
            CLI_LOGGER.warning("command.llm adapter_error=%s; falling back to regex", e)
            print(f"LLM unavailable ({e}); falling back to regex.")
            response = handle_command(command)
            CLI_LOGGER.info("command.regex result=%s", str(response)[:300])
            print(response)

if __name__ == "__main__":
    main()
