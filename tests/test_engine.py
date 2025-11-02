# test_engine.py
import os
import sys
import unittest

# allow running this test module directly by adding repo root to sys.path
repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from core import registry, engine

class EngineTests(unittest.TestCase):
    def setUp(self):
        # backup any existing skills we might overwrite
        self.orig_skills = {}
        for skill in ["create_folder", "delete_folder", "list_dir",
                      "read_file", "write_file", "move_file", "copy_file",
                      "create_file", "delete_file"]:
            self.orig_skills[skill] = registry.get_skill_meta(skill)
            registry.unregister_skill(skill)

    def tearDown(self):
        # restore original skills
        for skill, meta in self.orig_skills.items():
            registry.unregister_skill(skill)
            if meta:
                registry.SKILL_REGISTRY[skill] = meta

    # ---------------- CREATE FOLDER ---------------- #
    def test_create_folder(self):
        @registry.register_skill("create_folder", overwrite=True)
        def fake_create_folder(foldername, dest=None):
            return f"FOLDER_CREATED:{foldername}@{dest}"

        res = engine.handle_command("create folder named Projects in Desktop")
        self.assertIn("FOLDER_CREATED:Projects", res)

    # ---------------- DELETE FOLDER ---------------- #
    def test_delete_folder(self):
        @registry.register_skill("delete_folder", overwrite=True)
        def fake_delete_folder(foldername, dest=None, recursive=False):
            return f"FOLDER_DELETED:{foldername}@{dest}@recursive={recursive}"

        res = engine.handle_command("delete folder called Temp recursive")
        self.assertIn("recursive=True", res)

    # ---------------- LIST DIR ---------------- #
    def test_list_dir(self):
        @registry.register_skill("list_dir", overwrite=True)
        def fake_list_dir(path=None):
            return f"LISTED:{path}"

        res = engine.handle_command("list contents in Documents")
        self.assertIn("LISTED", res)

    # ---------------- READ FILE ---------------- #
    def test_read_file(self):
        @registry.register_skill("read_file", overwrite=True)
        def fake_read_file(filename, dest=None):
            return f"READ:{filename}@{dest}"

        res = engine.handle_command("read file notes.txt in Desktop")
        self.assertIn("READ:notes.txt", res)

    # ---------------- WRITE / APPEND FILE ---------------- #
    def test_write_file(self):
        @registry.register_skill("write_file", overwrite=True)
        def fake_write_file(filename, dest=None, content=None, append=False):
            return f"WRITE:{filename}@{dest}@content={content}@append={append}"

        # write
        res = engine.handle_command('write "Hello world" to file.txt in Documents')
        self.assertIn("content=Hello world", res)
        self.assertIn("append=False", res)

        # append
        res2 = engine.handle_command('append "More" to file.txt in Documents')
        self.assertIn("append=True", res2)

    # ---------------- MOVE FILE ---------------- #
    def test_move_file(self):
        @registry.register_skill("move_file", overwrite=True)
        def fake_move_file(src, dest):
            return f"MOVED:{src}@{dest}"

        res = engine.handle_command("move file.txt to Documents")
        self.assertIn("MOVED:file.txt@", res)

    # ---------------- COPY FILE ---------------- #
    def test_copy_file(self):
        @registry.register_skill("copy_file", overwrite=True)
        def fake_copy_file(src, dest):
            return f"COPIED:{src}@{dest}"

        res = engine.handle_command("copy file.txt to Documents")
        self.assertIn("COPIED:file.txt@", res)

    # ---------------- UNKNOWN COMMAND ---------------- #
    def test_unknown_command(self):
        res = engine.handle_command("do something impossible")
        self.assertIn("didn't understand", res)

    # ---------------- FILE CREATE / DELETE ---------------- #
    def test_create_file(self):
        @registry.register_skill("create_file", overwrite=True)
        def fake_create(filename, dest=None):
            return f"CREATED:{filename}@{dest}"

        res = engine.handle_command("create file named todo.txt in Desktop")
        self.assertIn("CREATED:todo.txt", res)

    def test_delete_file(self):
        @registry.register_skill("delete_file", overwrite=True)
        def fake_delete(filename, dest=None):
            return f"DELETED:{filename}@{dest}"

        res = engine.handle_command("delete file named todo.txt in Desktop")
        self.assertIn("DELETED:todo.txt", res)

    # ---------------- PERMISSION ENFORCEMENT ---------------- #
    def test_permission_enforcement(self):
        @registry.register_skill("create_file", permissions={"file"}, overwrite=True)
        def protected_create(filename, dest=None):
            return f"PROTECTED_CREATED:{filename}@{dest}"

        # without permissions -> denied
        res = engine.handle_command("create file named secret.txt")
        self.assertIn("Permission denied", res)

        # with permissions -> allowed
        res2 = engine.handle_command("create file named secret.txt", granted_permissions={"file"})
        self.assertIn("PROTECTED_CREATED:secret.txt", res2)

    # ---------------- NO-SKILL REGISTERED ---------------- #
    def test_no_skill_registered(self):
        # ensure create_file is unregistered
        registry.unregister_skill("create_file")
        res = engine.handle_command("create file named orphan.txt")
        self.assertIn("No skill found", res)

    # ---------------- SKILL EXCEPTION HANDLING ---------------- #
    def test_skill_exception_handling(self):
        @registry.register_skill("read_file", overwrite=True)
        def bad_read(filename, dest=None):
            raise RuntimeError("boom")

        res = engine.handle_command("read file nasty.txt")
        self.assertTrue(res.startswith("Error:"))

    # ---------------- AMBIGUOUS COMMAND ---------------- #
    def test_ambiguous_command(self):
        res = engine.handle_command("create and delete file todo.txt")
        self.assertIn("didn't understand", res)

    # ---------------- ABSOLUTE PATH WITH FILENAME ---------------- #
    def test_absolute_path_filename(self):
        @registry.register_skill("create_file", overwrite=True)
        def abs_create(filename, dest=None):
            return f"ABS_CREATED:{filename}@{dest}"

        # unix-style absolute path
        res = engine.handle_command("create /tmp/mylog.txt")
        self.assertIn("ABS_CREATED:mylog.txt", res)


if __name__ == "__main__":
    unittest.main()
