"""Tkinter integration tests; requires a graphical desktop or Xvfb."""
import time
from git_repo_manager.gui import GitRepoManager, path_key
from tests.support import GitFixture

class UiTests(GitFixture):
    @staticmethod
    def close_app(app):
        app.changes_view.destroy()
        # Cancel Tk timers before starting another application in this interpreter.
        for callback in app.tk.call("after", "info"):
            app.after_cancel(callback)
        app.destroy()

    def test_bulk_pull_continues_after_a_project_with_local_changes(self):
        healthy = self.root / "healthy"
        self.cmd(self.root, "clone", str(self.remote), str(healthy))
        self.commit(self.peer, "remote update\n")
        self.cmd(self.peer, "push")
        (self.source / "data.txt").write_text("local changes\n", encoding="utf-8")

        app = GitRepoManager(self.root, auto_scan=False, state_file=self.root / "pull-state.json")
        self.addCleanup(self.close_app, app)
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

        app.scan()
        wait_idle()
        paths = (self.source, healthy, self.peer)
        # Make the rejected project run first, followed by two valid projects.
        app.repos = {path_key(path): app.repos[path_key(path)] for path in paths}
        app.checked = set(app.repos)
        app.perform("pull")
        wait_idle()
        self.assertIn("Übersprungen: Lokale Änderungen", app.results[path_key(self.source)])
        self.assertEqual(app.results[path_key(healthy)], "Pull (ff-only) ✓")
        self.assertEqual(app.results[path_key(self.peer)], "Pull (ff-only) ✓")
        self.assertEqual((self.source / "data.txt").read_text(), "local changes\n")
        self.assertEqual((healthy / "data.txt").read_text(), "remote update\n")
        self.assertIn("Lokale Änderungen", app.log.get("1.0", "end"))
        self.assertIn("2 erfolgreich", app.status_text.get())
        self.assertIn("1 übersprungen · 0 fehlgeschlagen", app.status_text.get())
        app.tree.selection_set(path_key(self.source))
        app.update()
        self.assertIn("zuerst committen oder stashen", app.detail_info.get())
        deadline = time.monotonic() + 10
        while not app.changes_view.files.get_children() and time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        self.assertEqual(len(app.changes_view.files.get_children()), 1)
        app.changes_view.files.selection_set("0")
        deadline = time.monotonic() + 10
        while "+local changes" not in app.changes_view.preview.get("1.0", "end") and time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        self.assertIn("+local changes", app.changes_view.preview.get("1.0", "end"))
        self.assertTrue(app.changes_view.preview.tag_ranges("add"))
        app.tree.selection_set(path_key(healthy))
        deadline = time.monotonic() + 10
        while "Arbeitsverzeichnis ist sauber" not in app.changes_view.preview.get("1.0", "end") and time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        self.assertIn("Arbeitsverzeichnis ist sauber", app.changes_view.preview.get("1.0", "end"))
        self.assertFalse(app.changes_view.files.get_children())
        self.assertFalse(callback_errors, str(callback_errors))

    def test_scan_check_filter_branch_details_and_bulk_fetch(self):

        app = GitRepoManager(self.root, auto_scan=False, state_file=self.root / "ui-state.json")
        self.addCleanup(self.close_app, app)
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
        # Project buttons act on the highlighted project, even when another is checked.
        app.project_action_buttons["fetch"].invoke()
        wait_idle()
        self.assertEqual(app.results[path_key(self.peer)], "Fetch ✓")
        self.assertNotIn(source_key, app.results)
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
        app.update_idletasks()
        self.assertTrue(app.empty_label.winfo_ismapped())
        app.only_dirty.set(True)
        app.search.set("no-matching-project")
        app._clear_filters()
        self.assertFalse(app.only_checked.get())
        self.assertFalse(app.only_dirty.get())
        self.assertEqual(app.search.get(), "")
        self.assertEqual(len(app.tree.get_children()), 3)
        self.assertFalse(app.empty_label.winfo_ismapped())
        app.check_visible()
        self.assertEqual(len(app.checked), 3)
        app.refresh()
        wait_idle()
        self.assertEqual(len(app.checked), 3)
        app.clear_checks()
        self.assertTrue(app.action_buttons["push"].instate(["disabled"]))
        app._save_state()
        self.assertTrue((self.root / "ui-state.json").exists())

        nested = self.source / "nested"
        nested.mkdir()
        self.cmd(nested, "init", "-b", "main")
        self.assertFalse(app.recursive_search.get())
        app.scan()
        self.assertTrue(app.recursive_search_box.instate(["disabled"]))
        wait_idle()
        self.assertEqual(len(app.repos), 3)
        self.assertFalse(app._read_state()["recursive_search"])
        self.assertFalse(app.recursive_search_box.instate(["disabled"]))
        app.recursive_search_box.invoke()
        app.scan()
        wait_idle()
        self.assertEqual(len(app.repos), 4)
        self.assertIn(path_key(nested), app.repos)
        self.assertTrue(app._read_state()["recursive_search"])

        # Main actions remain reachable at the minimum supported window size.
        app.geometry("1080x700")
        app.update()
        for widget in (app.scan_button, app.search_entry, app.tree, app.detail_tabs,
                       *app.action_buttons.values(), *app.project_action_buttons.values(),
                       app.changes_view.files, app.changes_view.preview,
                       app.refresh_button, app.stop_button):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                 app.winfo_rootx() + app.winfo_width())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                 app.winfo_rooty() + app.winfo_height())
