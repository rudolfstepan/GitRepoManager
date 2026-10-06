"""Git operations for the desktop UI; Python standard library only."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator
from .windows_job import ProcessJob

DEPENDENCY_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache"}
ALWAYS_SKIP = {".git", ".hg", ".svn", "$RECYCLE.BIN", "System Volume Information"}
ACTIONS = {"fetch": "Fetch", "pull": "Pull (ff-only)", "push": "Push"}


@dataclass
class GitResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.cancelled

    @property
    def output(self) -> str:
        return "\n".join(s.strip() for s in (self.stdout, self.stderr) if s.strip())


@dataclass
class Branch:
    name: str
    remote: bool = False
    current: bool = False
    upstream: str = ""
    tracking: str = ""
    commit: str = ""


@dataclass
class Repository:
    path: Path
    branch: str = ""
    upstream: str = ""
    upstream_remote: str = ""
    upstream_ref: str = ""
    ahead: int = 0
    behind: int = 0
    changed: int = 0
    untracked: int = 0
    conflicts: int = 0
    detached: bool = False
    unborn: bool = False
    bare: bool = False
    branches: list[Branch] = field(default_factory=list)
    remotes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def dirty(self) -> bool:
        return bool(self.changed or self.untracked or self.conflicts)

    @property
    def status(self) -> str:
        if self.error:
            return "Fehler beim Lesen"
        if self.bare:
            return "Bare-Repository"
        if self.conflicts:
            return f"{self.conflicts} Konflikt(e)"
        parts = []
        if self.changed:
            parts.append(f"{self.changed} geändert")
        if self.untracked:
            parts.append(f"{self.untracked} neu")
        return " · ".join(parts) or ("Noch kein Commit" if self.unborn else "Sauber")


def _stop_process(process: subprocess.Popen, job: ProcessJob) -> None:
    """Terminate Git and its SSH/credential children as well."""
    if job.terminate():
        return
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()


def _git_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", LC_ALL="C")
    return env


def git(path: Path, *args: str, cancel: threading.Event | None = None,
        timeout: float = 45) -> GitResult:
    command = ["git", "--no-optional-locks", "-C", str(path), "-c", "color.ui=false", *args]
    if cancel is not None and cancel.is_set():
        return GitResult(command, -1, stderr="Abgebrochen.", cancelled=True)
    env = _git_environment()
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, **options,
        )
    except OSError as exc:
        return GitResult(command, -1, stderr=str(exc))
    with ProcessJob(process) as job:
        deadline = time.monotonic() + timeout
        while True:
            cancelled = cancel is not None and cancel.is_set()
            expired = time.monotonic() >= deadline
            if cancelled or expired:
                _stop_process(process, job)
                try:
                    out, err = process.communicate(timeout=2)
                except subprocess.TimeoutExpired as exc:
                    # Keep the UI responsive even when an external helper retains a pipe.
                    out, err = exc.output or b"", exc.stderr or b""
                reason = ("Abgebrochen; bereits übertragene Änderungen bleiben bestehen."
                          if cancelled else f"Zeitlimit nach {timeout:g} Sekunden erreicht.")
                return GitResult(command, -1, out.decode("utf-8", "replace"),
                                 err.decode("utf-8", "replace") + "\n" + reason, cancelled)
            try:
                out, err = process.communicate(timeout=0.15)
                return GitResult(command, process.returncode, out.decode("utf-8", "replace"),
                                 err.decode("utf-8", "replace"))
            except subprocess.TimeoutExpired:
                continue


def discover_repositories(
    root: Path, cancel: threading.Event | None = None, skip_dependencies: bool = False,
    on_error: Callable[[str], None] | None = None,
    on_progress: Callable[[int, Path], None] | None = None,
) -> Iterator[Path]:
    """Find normal, nested, bare and linked-worktree repositories without following links."""
    pending = [root.resolve()]
    visited = 0
    while pending:
        if cancel is not None and cancel.is_set():
            return
        folder = pending.pop()
        try:
            with os.scandir(folder) as iterator:
                entries = {entry.name: entry for entry in iterator}
            visited += 1
            if on_progress and visited % 200 == 0:
                on_progress(visited, folder)
            marker = entries.get(".git")
            bare = (
                "HEAD" in entries and entries["HEAD"].is_file(follow_symlinks=False)
                and "objects" in entries and entries["objects"].is_dir(follow_symlinks=False)
                and "config" in entries and ("refs" in entries or "packed-refs" in entries)
            )
            if marker is not None or bare:
                yield folder
            if bare:
                continue
            for name, entry in entries.items():
                if name in ALWAYS_SKIP or (skip_dependencies and name in DEPENDENCY_DIRS):
                    continue
                is_junction = getattr(entry, "is_junction", lambda: False)
                if entry.is_dir(follow_symlinks=False) and not is_junction():
                    pending.append(Path(entry.path))
        except OSError as exc:
            if on_error:
                on_error(f"Ordner nicht lesbar: {folder}: {exc}")


def parse_status(repo: Repository, output: str) -> None:
    records = iter(output.split("\0"))
    oid = ""
    for record in records:
        if record.startswith("# branch.head "):
            repo.branch = record[14:]
            repo.detached = repo.branch == "(detached)"
        elif record.startswith("# branch.oid "):
            oid = record[13:]
            repo.unborn = oid == "(initial)"
        elif record.startswith("# branch.upstream "):
            repo.upstream = record[18:]
        elif record.startswith("# branch.ab "):
            ahead, behind = record[12:].split()
            repo.ahead, repo.behind = int(ahead[1:]), int(behind[1:])
        elif record.startswith(("1 ", "2 ")):
            repo.changed += 1
            if record.startswith("2 "):
                next(records, None)  # Original filename in a rename record.
        elif record.startswith("u "):
            repo.conflicts += 1
        elif record.startswith("? "):
            repo.untracked += 1
    if repo.detached:
        repo.branch = f"Detached {oid[:8]}"


def read_repository(path: Path, cancel: threading.Event | None = None) -> Repository:
    repo = Repository(path=path)
    kind = git(path, "rev-parse", "--is-bare-repository", cancel=cancel)
    if not kind.ok:
        repo.error = kind.output
        return repo
    repo.bare = kind.stdout.strip() == "true"
    if repo.bare:
        head = git(path, "symbolic-ref", "--quiet", "--short", "HEAD", cancel=cancel)
        repo.branch = head.stdout.strip() or "—"
    else:
        status = git(path, "status", "--porcelain=v2", "-z", "--branch",
                     "--untracked-files=normal", cancel=cancel)
        if not status.ok:
            repo.error = status.output
            return repo
        parse_status(repo, status.stdout)
    refs = git(
        path, "for-each-ref",
        "--format=%(HEAD)%00%(refname)%00%(upstream:short)%00%(upstream:track)%00%(objectname:short)%00%(symref)%00%(upstream:remotename)%00%(upstream:remoteref)",
        "refs/heads", "refs/remotes", cancel=cancel,
    )
    if not refs.ok:
        repo.error = refs.output
        return repo
    for line in refs.stdout.splitlines():
        fields = line.split("\0")
        if len(fields) != 8:
            continue
        current, name, upstream, tracking, commit, symbolic, remote_name, remote_ref = fields
        remote = name.startswith("refs/remotes/")
        if remote and symbolic:
            continue
        name = name.removeprefix("refs/remotes/").removeprefix("refs/heads/")
        repo.branches.append(Branch(name, remote, current == "*", upstream, tracking, commit))
        if current == "*":
            repo.upstream_remote, repo.upstream_ref = remote_name, remote_ref
    remotes = git(path, "remote", cancel=cancel)
    if remotes.ok:
        repo.remotes = remotes.stdout.splitlines()
    else:
        repo.error = remotes.output
    return repo


def run_action(repo: Repository, action: str, cancel: threading.Event | None = None) -> GitResult:
    if action not in ACTIONS:
        raise ValueError(f"Unbekannte Aktion: {action}")
    if repo.error:
        return GitResult([], 1, stderr=f"Repository nicht lesbar: {repo.error}")
    if not repo.remotes:
        return GitResult([], 1, stderr="Kein Remote konfiguriert.")
    if action != "fetch":
        if repo.bare:
            return GitResult([], 1, stderr="Für Bare-Repositories steht hier nur Fetch zur Verfügung.")
        if repo.detached or repo.unborn:
            return GitResult([], 1, stderr="Ein lokaler Branch mit mindestens einem Commit ist erforderlich.")
        if not repo.upstream_remote or not repo.upstream_ref or repo.upstream_remote == ".":
            return GitResult([], 1, stderr="Kein Remote-Upstream für diesen Branch konfiguriert. Bitte zuerst in Git einrichten.")
    if action == "pull" and repo.dirty:
        return GitResult([], 1, stderr="Pull übersprungen: lokale Änderungen zuerst committen oder stashen.")
    commands = {
        "fetch": ("fetch", "--all", "--prune"),
        "pull": ("pull", "--ff-only", "--no-rebase", "--no-autostash"),
        # Explicit destination and refspec prevent matching/mirror/followTags config
        # from accidentally publishing other branches or tags.
        "push": ("-c", f"remote.{repo.upstream_remote}.mirror=false", "push", "--no-force", "--no-mirror", "--no-follow-tags",
                 "--recurse-submodules=no", "--", repo.upstream_remote,
                 f"refs/heads/{repo.branch}:{repo.upstream_ref}"),
    }
    return git(repo.path, *commands[action], cancel=cancel, timeout=300)
