"""Tkinter integration tests; requires a graphical desktop or Xvfb."""
import time
from git_repo_manager.gui import GitRepoManager, path_key
from tests.support import GitFixture

class UiTests(GitFixture):
    def test_scan_check_filter_branch_details_and_bulk_fetch(self):

        app = GitRepoManager(self.root, auto_scan=False, state_file=self.root / "ui-state.json")
        self.addCleanup(app.destroy)
        callback_errors = []
        app.report_callback_exception = lambda *exc: callback_errors.append(exc)

        def wait_idle():
            deadline = time.monotonic() + 20
            while app.busy and time.monotonic() < deadline:
                app.update()
                time.sleep(0.02)
            app.update()
            self.assertFalse(app.busy, "UI worker timed out")
            self.assertFalse(callback_errors, str(callback_errors))

        app.update()
        app.scan()
        wait_idle()
        self.assertEqual(len(app.repos), 3)
        source_key = path_key(self.source)
        app.tree.selection_set(source_key)
        app.update()
        self.assertIn("main", app.detail_info.get())
        self.assertGreaterEqual(len(app.branch_tree.get_children()), 2)
        app._toggle(source_key)
        self.assertIn(source_key, app.checked)
        app.search.set("peer")
        app.update()
        self.assertEqual(len(app.tree.get_children()), 1)
        self.assertIn("1 ausgeblendet", app.stats_text.get())
        self.assertFalse(app.action_buttons["fetch"].instate(["disabled"]))
        app.perform("fetch")
        wait_idle()
        self.assertEqual(app.results[source_key], "Fetch ✓")
        app.search.set("")
        app.only_checked.set(True)
        app._render()
        self.assertEqual(app.tree.get_children(), (source_key,))
        app._toggle_all()
        self.assertEqual(len(app.tree.get_children()), 0)
        app.only_checked.set(False)
        app._render()
        app.check_visible()
        self.assertEqual(len(app.checked), 3)
        app.refresh()
        wait_idle()
        self.assertEqual(len(app.checked), 3)
        app.clear_checks()
        self.assertTrue(app.action_buttons["push"].instate(["disabled"]))
        app._save_state()
        self.assertTrue((self.root / "ui-state.json").exists())
