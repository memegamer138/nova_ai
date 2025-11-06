import os
import sys
import unittest
from unittest.mock import patch

# Ensure src/ is on sys.path so tests can import the package when run directly
repo_root = os.path.dirname(os.path.dirname(__file__))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from nova_ai.mcp import ollama_adapter


class OllamaAdapterTests(unittest.TestCase):
    def test_prompt_to_json(self):
        prompt = "create a new file called demo.txt on desktop"
        # Mock the CLI call so tests don't require an installed Ollama binary
        sample_raw = '{"action":"create_file","args":{"filename":"demo.txt","dest":"~/Desktop","content":""}}'
        with patch("nova_ai.mcp.ollama_adapter._run_ollama_cli", return_value=sample_raw):
            result = ollama_adapter.prompt_to_action(prompt, model="phi3")
        print("Model output:", result)

        self.assertIn("action", result)
        self.assertIn(result["action"], ollama_adapter.ALLOWED_ACTIONS)
        self.assertIsInstance(result["args"], dict)

    def test_invalid_action_rejected(self):
        raw = '{"action":"format_disk","args":{}}'
        with self.assertRaises(ollama_adapter.AdapterError):
            ollama_adapter.parse_and_validate(raw)

    def test_send_prompt_to_ollama_live(self):
        """Send a realistic prompt to the local Ollama CLI and verify the model returns the expected JSON shape.
        This test SKIPS if `ollama` is not on PATH so it won't fail CI environments that don't have Ollama installed.
        It does NOT execute any filesystem actions — it only inspects the adapter output.
        """
        import shutil
        if not shutil.which("ollama"):
            self.skipTest("ollama CLI not installed on PATH; skipping live model test")

        prompt = 'Create a folder called Projects and put a file called notes.txt in it. The text file should contain "Buy groceries".'
        # Call the adapter against the real local model. Increase timeout to allow pulls.
        parsed = ollama_adapter.prompt_to_action(prompt, timeout=60)

        # Basic contract checks
        self.assertIn("action", parsed)
        self.assertIn("args", parsed)

        # Support single action or batch of actions
        if parsed["action"] == "batch":
            actions = parsed["args"].get("actions", [])
            # find create_file action in batch
            create_file = None
            for a in actions:
                if a.get("action") == "create_file":
                    create_file = a
                    break
            self.assertIsNotNone(create_file, "batch did not contain a create_file action")
            args = create_file.get("args", {})
        else:
            args = parsed["args"]

        self.assertIsInstance(args, dict)

        # filename should mention notes (accept slight variations like notes.txt or note.txt)
        filename = args.get("filename", "") or args.get("file_path", "")
        filename = filename.lower()
        self.assertTrue("note" in filename)

        # dest should mention Projects (model may put it under Desktop/Projects or use file_path)
        dest = args.get("dest", "") or args.get("file_path", "")
        self.assertIn("projects", dest.lower())

        # content should include the requested text
        content = args.get("content", "")
        self.assertIn("buy groceries", content.lower())

# TODO: Check ollama installation
if __name__ == "__main__":
    unittest.main()