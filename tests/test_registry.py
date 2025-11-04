import os
import sys
import unittest

# make src/ available so tests can import the nova_ai package when running
repo_root = os.path.dirname(os.path.dirname(__file__))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.nova_ai.core import registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        # ensure clean state for test intents
        registry.unregister_skill("test.intent")
        registry.unregister_skill("dup.intent")

    def tearDown(self):
        registry.unregister_skill("test.intent")
        registry.unregister_skill("dup.intent")

    def test_register_and_list(self):
        @registry.register_skill("test.intent", permissions={"test"}, overwrite=True, description="a test")
        def handler(x=None):
            return "ok"

        meta = registry.get_skill_meta("test.intent")
        self.assertIsNotNone(meta)
        self.assertIn("test", meta.get("permissions"))
        self.assertEqual(meta.get("description"), "a test")
        self.assertIs(registry.get_skill("test.intent"), handler)

    def test_duplicate_registration_raises(self):
        @registry.register_skill("dup.intent", permissions={"a"}, overwrite=True)
        def h1():
            return 1

        # second registration without overwrite should raise
        with self.assertRaises(ValueError):
            @registry.register_skill("dup.intent", permissions={"b"}, overwrite=False)
            def h2():
                return 2

        # cleanup then allow overwrite
        registry.unregister_skill("dup.intent")

        @registry.register_skill("dup.intent", permissions={"b"}, overwrite=False)
        def h3():
            return 3


if __name__ == "__main__":
    unittest.main()
