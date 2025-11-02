import unittest

from core import registry, engine


class EngineDispatchTests(unittest.TestCase):
    def setUp(self):
        # preserve original create_file registration if present
        self.orig_create = registry.get_skill_meta("create_file")
        registry.unregister_skill("create_file")

    def tearDown(self):
        # restore original
        registry.unregister_skill("create_file")
        if self.orig_create:
            registry.SKILL_REGISTRY["create_file"] = self.orig_create

    def test_dispatch_with_permissions(self):
        @registry.register_skill("create_file", permissions={"file"}, overwrite=True)
        def fake_create(filename, dest=None):
            return f"CREATED:{filename}@{dest}"

        # allowed
        res = engine.handle_command("create file named sample.txt", granted_permissions={"file"})
        self.assertTrue(isinstance(res, str))
        self.assertIn("CREATED:sample.txt", res)

        # denied without permissions
        res2 = engine.handle_command("create file named sample.txt", granted_permissions=set())
        self.assertIn("Permission denied", res2)


if __name__ == "__main__":
    unittest.main()
