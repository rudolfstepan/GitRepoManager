"""Shared integration fixture isolated from the user's Git configuration."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from git_repo_manager.git_backend import git, _git_environment

class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-manager-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        settings = {
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "UI Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "UI Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        def isolated_git_environment():
            env = _git_environment()
            env.update(settings)
            return env
        # Isolate Git's children without changing Tcl's native process environment.
        environment = patch("git_repo_manager.git_backend._git_environment", isolated_git_environment)
        environment.start()
        self.addCleanup(environment.stop)
        self.source = self.root / "Quelle mit Leerzeichen"
        self.remote = self.root / "remote.git"
        self.peer = self.root / "peer"
        self.source.mkdir()
        self.cmd(self.source, "init", "-b", "main")
        (self.source / "data.txt").write_text("initial\n", encoding="utf-8")
        self.cmd(self.source, "add", ".")
        self.cmd(self.source, "commit", "-m", "Initial")
        self.cmd(self.root, "init", "--bare", "-b", "main", str(self.remote))
        self.cmd(self.source, "remote", "add", "origin", str(self.remote))
        self.cmd(self.source, "push", "-u", "origin", "main")
        self.cmd(self.root, "clone", str(self.remote), str(self.peer))

    def cmd(self, path, *args):
        result = git(path, *args)
        self.assertTrue(result.ok, result.output)
        return result.stdout.strip()

    def commit(self, repo, content, filename="data.txt"):
        (repo / filename).write_text(content, encoding="utf-8")
        self.cmd(repo, "add", "--", filename)
        self.cmd(repo, "commit", "-m", content.strip() or "Update")
