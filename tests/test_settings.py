"""Settings migration and source-layout regression checks."""
import json
from pathlib import Path
import tempfile
import unittest

from git_repo_manager.settings import default_scan_root, load_state, save_state, source_root


class SettingsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="git-manager-settings-")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_legacy_settings_are_preserved_and_new_settings_take_precedence(self):
        old = self.root / ".git-repo-manager.json"
        new = self.root / "config" / "state.json"
        old_text = json.dumps({"root": "projects", "checked": ["repo-a"], "geometry": "1200x800"})
        old.write_text(old_text, encoding="utf-8")
        state = load_state(new, fallback=old)
        self.assertEqual(state["checked"], ["repo-a"])
        save_state(new, {**state, "root": "another-folder"})
        self.assertEqual(load_state(new, fallback=old)["root"], "another-folder")
        self.assertEqual(old.read_text(encoding="utf-8"), old_text)
        self.assertFalse(new.with_suffix(".json.tmp").exists())

    def test_invalid_settings_do_not_prevent_startup(self):
        path = self.root / "state.json"
        for content in ("broken json", "[]", "null"):
            path.write_text(content, encoding="utf-8")
            self.assertEqual(load_state(path), {})
        path.write_text(json.dumps({"root": 123, "checked": ["valid", 7], "unknown": "ignored"}))
        self.assertEqual(load_state(path), {"checked": ["valid"], "skip_dependencies": False,
                                           "recursive_search": False})

    def test_source_checkout_still_scans_the_workspace_parent(self):
        project = Path(__file__).resolve().parents[1]
        self.assertEqual(source_root(), project)
        self.assertEqual(default_scan_root(), project.parent)
