"""Repository discovery, Git operations and cancellation integration tests."""
import threading
import time
from git_repo_manager.git_backend import discover_repositories, git, read_repository, run_action
from tests.support import GitFixture

class BackendTests(GitFixture):
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
        self.assertIn("lokale Änderungen", result.output)
        (self.source / "untracked.txt").unlink()
        self.commit(self.peer, "peer commit\n")
        self.cmd(self.peer, "push")
        self.commit(self.source, "local divergent commit\n")
        before = self.cmd(self.source, "rev-parse", "HEAD")
        result = run_action(read_repository(self.source), "pull")
        self.assertFalse(result.ok)
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
