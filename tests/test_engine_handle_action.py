import unittest
import sys
import os
# ensure src is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))

from nova_ai.core import engine
from nova_ai.core.registry import register_skill, unregister_skill


class EngineHandleActionTests(unittest.TestCase):
    def setUp(self):
        # register a simple test skill
        @register_skill("test_noop", permissions=None, overwrite=True, description="noop for tests")
        def test_noop(**kwargs):
            return {"status": "success", "echo": kwargs}

    def tearDown(self):
        try:
            unregister_skill("test_noop")
        except Exception:
            pass

    def test_single_action_executes(self):
        action = {"action": "test_noop", "args": {"foo": "bar"}}
        res = engine.handle_action(action)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("echo", {}).get("foo"), "bar")

    def test_batch_action_executes(self):
        actions = {"action": "batch", "args": {"actions": [
            {"action": "test_noop", "args": {"a": 1}},
            {"action": "test_noop", "args": {"b": 2}}
        ]}}
        res = engine.handle_action(actions)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "batch")
        results = res.get("results")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].get("status"), "success")
        self.assertEqual(results[1].get("status"), "success")

    def test_requires_confirmation_for_destructive(self):
        action = {"action": "delete_file", "args": {"filename": "important.txt"}}
        res = engine.handle_action(action)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "requires_confirmation")
        pending = res.get("pending")
        self.assertTrue(isinstance(pending, list) and len(pending) >= 1)
        self.assertEqual(pending[0].get("action"), "delete_file")

    def test_confirmation_allows_execution(self):
        # need to register a fake delete_file skill to avoid touching FS
        @register_skill("delete_file", permissions=None, overwrite=True, description="fake delete")
        def fake_delete(filename=None, dest=None):
            return {"status": "success", "deleted": filename}

        try:
            action = {"action": "delete_file", "args": {"filename": "x.txt", "confirm": True}}
            res = engine.handle_action(action)
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("deleted"), "x.txt")
        finally:
            try:
                unregister_skill("delete_file")
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
