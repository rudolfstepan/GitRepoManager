"""Repository discovery, Git operations and cancellation integration tests."""
import threading
import time
from git_repo_manager.git_backend import (discover_repositories, git, read_repository, run_action,
                                         read_local_changes, read_change_diff)
from tests.support import GitFixture

class BackendTests(GitFixture):
    def test_local_changes_show_index_worktree_and_new_files(self):
        (self.source / "data.txt").write_text("staged content\n")
        self.cmd(self.source, "add", "data.txt")
        (self.source / "data.txt").write_text("unstaged content\n")
        (self.source / "neu ä.txt").write_text("new content\n", encoding="utf-8")
        (self.source / "binary.dat").write_bytes(b"\x00\x01\x02")
        changes = {(c.path, c.area): c for c in read_local_changes(self.source)}
        self.assertEqual(len(changes), 4)
        staged = read_change_diff(self.source, changes["data.txt", "Vorgemerkt"])
        unstaged = read_change_diff(self.source, changes["data.txt", "Nicht vorgemerkt"])
        self.assertIn("-initial", staged)
        self.assertIn("+staged content", staged)
        self.assertIn("-staged content", unstaged)
        self.assertIn("+unstaged content", unstaged)
        self.assertIn("new content", read_change_diff(self.source, changes["neu ä.txt", "Neu"]))
        self.assertIn("Binärdatei", read_change_diff(self.source, changes["binary.dat", "Neu"]))
        self.assertEqual(self.cmd(self.source, "show", ":data.txt"), "staged content")

    def test_local_changes_rename_delete_and_initial_commit(self):
        self.cmd(self.source, "mv", "data.txt", "renamed ä.txt")
        change, = read_local_changes(self.source)
        self.assertEqual((change.path, change.original_path), ("renamed ä.txt", "data.txt"))
        self.assertIn("rename from data.txt", read_change_diff(self.source, change))
        self.cmd(self.source, "commit", "-m", "Rename")
        (self.source / "renamed ä.txt").unlink()
        change, = read_local_changes(self.source)
        self.assertEqual(change.status, "Gelöscht")
        self.assertIn("-initial", read_change_diff(self.source, change))
        empty = self.root / "empty"
        empty.mkdir()
        self.cmd(empty, "init", "-b", "main")
        (empty / "first.txt").write_text("first content\n")
        self.cmd(empty, "add", ".")
        change, = read_local_changes(empty)
        self.assertIn("+first content", read_change_diff(empty, change))

    def test_scan_finds_nested_bare_worktree_and_optional_dependencies(self):
        nested = self.source / "nested"
        nested.mkdir()
        self.cmd(nested, "init", "-b", "main")
        linked = self.root / "linked"
        self.cmd(self.source, "worktree", "add", "-b", "linked-branch", str(linked))
        dependency = self.root / "node_modules" / "package"
        dependency.mkdir(parents=True)
        self.cmd(dependency, "init", "-b", "main")
        found = set(discover_repositories(self.root))
        self.assertEqual(found, {self.source, self.remote, self.peer, nested, linked, dependency})
        self.assertNotIn(dependency, set(discover_repositories(self.root, skip_dependencies=True)))
        self.assertEqual(set(discover_repositories(self.root, recursive=False)),
                         {self.source, self.remote, self.peer, linked})
        self.assertEqual(set(discover_repositories(self.source, recursive=False)),
                         {self.source, nested})
        self.assertEqual(set(discover_repositories(self.remote, recursive=False)), {self.remote})
        linked_repo = read_repository(linked)
        self.assertEqual(linked_repo.branch, "linked-branch")
        self.assertFalse(linked_repo.error)

    def test_status_tracks_changes_unicode_and_rename(self):
        self.cmd(self.source, "branch", "feature/demo")
        self.cmd(self.source, "mv", "data.txt", "umbenannt ü.txt")
        (self.source / "neu ä.txt").write_text("untracked", encoding="utf-8")
        repo = read_repository(self.source)
        self.assertFalse(repo.error)
        self.assertEqual(repo.branch, "main")
        self.assertEqual(repo.upstream, "origin/main")
        self.assertEqual((repo.upstream_remote, repo.upstream_ref), ("origin", "refs/heads/main"))
        self.assertEqual((repo.changed, repo.untracked), (1, 1))
        self.assertIn("feature/demo", [b.name for b in repo.branches])
        self.assertIn("origin/main", [b.name for b in repo.branches if b.remote])

    def test_push_fetch_pull_end_to_end(self):
        self.commit(self.peer, "remote change\n")
        self.assertTrue(run_action(read_repository(self.peer), "push").ok)
        self.assertTrue(run_action(read_repository(self.source), "fetch").ok)
        self.assertEqual(read_repository(self.source).behind, 1)
        pull = run_action(read_repository(self.source), "pull")
        self.assertTrue(pull.ok, pull.output)
        self.assertEqual((self.source / "data.txt").read_text(), "remote change\n")
        self.commit(self.source, "local change\n")
        self.assertEqual(read_repository(self.source).ahead, 1)
        push = run_action(read_repository(self.source), "push")
        self.assertTrue(push.ok, push.output)
        self.assertEqual(self.cmd(self.source, "rev-parse", "HEAD"),
                         self.cmd(self.remote, "rev-parse", "refs/heads/main"))

    def test_push_ignores_mirror_matching_and_tag_settings(self):
        self.cmd(self.source, "branch", "do-not-publish")
        self.commit(self.source, "push one branch\n")
        self.cmd(self.source, "tag", "-a", "do-not-publish-tag", "-m", "Private tag")
        self.cmd(self.source, "config", "push.default", "matching")
        self.cmd(self.source, "config", "push.followTags", "true")
        self.cmd(self.source, "config", "remote.origin.mirror", "true")
        self.cmd(self.source, "config", "remote.origin.push", "+refs/heads/*:refs/heads/*")
        result = run_action(read_repository(self.source), "push")
        self.assertTrue(result.ok, result.output)
        refs = self.cmd(self.remote, "for-each-ref", "--format=%(refname)")
        self.assertEqual(refs, "refs/heads/main")

    def test_pull_refuses_dirty_and_divergent_worktrees(self):
        (self.source / "untracked.txt").write_text("keep me")
        before = self.cmd(self.source, "rev-parse", "HEAD")
        result = run_action(read_repository(self.source), "pull")
        self.assertFalse(result.ok)
        self.assertTrue(result.skipped)
        self.assertIn("Lokale Änderungen", result.output)
        (self.source / "untracked.txt").unlink()
        self.commit(self.peer, "peer commit\n")
        self.cmd(self.peer, "push")
        self.commit(self.source, "local divergent commit\n")
        before = self.cmd(self.source, "rev-parse", "HEAD")
        result = run_action(read_repository(self.source), "pull")
        self.assertFalse(result.ok)
        self.assertFalse(result.skipped)
        self.assertEqual(self.cmd(self.source, "rev-parse", "HEAD"), before)
        self.assertFalse((self.source / ".git" / "MERGE_HEAD").exists())

    def test_detached_unborn_and_missing_upstream(self):
        self.cmd(self.source, "checkout", "--detach")
        repo = read_repository(self.source)
        self.assertTrue(repo.detached)
        self.assertTrue(repo.branch.startswith("Detached "))
        self.assertFalse(run_action(repo, "push").ok)
        empty = self.root / "empty"
        empty.mkdir()
        self.cmd(empty, "init", "-b", "new-main")
        repo = read_repository(empty)
        self.assertTrue(repo.unborn)
        self.assertEqual(repo.branch, "new-main")
        self.assertFalse(run_action(repo, "fetch").ok)
        self.cmd(self.peer, "branch", "--unset-upstream")
        self.assertFalse(run_action(read_repository(self.peer), "push").ok)

    def test_fetch_prunes_deleted_remote_branch(self):
        self.cmd(self.peer, "push", "origin", "main:obsolete")
        self.assertTrue(run_action(read_repository(self.source), "fetch").ok)
        self.assertIn("origin/obsolete", [b.name for b in read_repository(self.source).branches])
        self.cmd(self.peer, "push", "origin", "--delete", "obsolete")
        self.assertTrue(run_action(read_repository(self.source), "fetch").ok)
        self.assertNotIn("origin/obsolete", [b.name for b in read_repository(self.source).branches])

    def test_cancellation_stops_running_git_child(self):
        cancel = threading.Event()
        timer = threading.Timer(0.4, cancel.set)
        timer.start()
        start = time.monotonic()
        try:
            result = git(self.source, "-c", "alias.wait-test=!sleep 15", "wait-test",
                         cancel=cancel, timeout=20)
        finally:
            timer.cancel()
        self.assertTrue(result.cancelled, result.output)
        self.assertLess(time.monotonic() - start, 7)

    def test_timeout_stops_running_git_child(self):
        start = time.monotonic()
        result = git(self.source, "-c", "alias.wait-test=!sleep 15", "wait-test", timeout=0.3)
        self.assertFalse(result.ok)
        self.assertIn("Zeitlimit", result.output)
        self.assertLess(time.monotonic() - start, 7)
