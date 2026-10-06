# Architecture

[Documentation](../README.md) · [Deutsch](../de/architecture.md)

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `gui.py` | Tk widgets, filtering, selection, rendering and background job orchestration. |
| `git_backend.py` | Repository discovery, Git subprocess execution, status parsing, models and batch-action policy. |
| `settings.py` | User-profile paths, source-checkout defaults, validated settings and legacy migration. |
| `windows_job.py` | Windows job objects for cancelling Git and its descendant processes. |
| `__init__.py` | Package identity and the single version value. |
| `__main__.py` | Installed module entry point. |
| Root `app.py` | Thin source-checkout launcher; no duplicate application logic. |

Runtime dependencies are Python's standard library, Tcl/Tk and the installed Git
executable. Packaging and optional developer tools are separate from runtime code.

## Discovery and status

The scanner uses an iterative directory walk. It recognizes `.git` directories
and files, and bare-repository markers. It continues inside working trees to
find nested repositories but skips Git internals and directory links.

During scans, up to four workers read repository status. Git's porcelain v2
output with NUL delimiters is parsed without depending on localized human output.
A rename consumes its following original-path record. Branch information comes
from `for-each-ref`; remote HEAD aliases are omitted.

`Repository`, `Branch` and `GitResult` dataclasses carry data into the UI.
Git paths and arguments are passed as an argument list without a shell.
Read operations disable optional Git locks.

## UI and background work

Tk calls stay on the main thread. Workers put repository snapshots, messages,
results and completion events into a thread-safe queue. The UI drains it every
80 milliseconds, preserving checkbox state while rebuilding the visible list.

Repository paths are normalized for row identity, so projects with the same name
remain distinct. Search changes visibility, not membership of the checked set.

Batch actions run sequentially. Each repository is read again before its action;
results are recorded independently and status is reloaded afterwards.
Errors do not interrupt the rest of the selection.

## Git policy and cancellation

Fetch covers all remotes and prunes remote-tracking refs. Pull requires a clean
working tree and uses fast-forward-only behavior without rebase or automatic
stash. Push supplies both the upstream remote and an explicit refspec, overriding
mirror/tag-following behavior for that call.

A cancellation event is checked between repositories and while communicating
with Git. Windows job objects track descendants, with a taskkill fallback.
On other systems, Git starts in its own process group. Timeouts use the same
termination path. Cancellation does not reverse operations already completed.

Git ownership checks stay enabled. Authentication uses the environment's normal
Git/SSH setup; terminal and Git Credential Manager interactive prompts are disabled.

## Settings and packaging

The source layout lives in `src/git_repo_manager/`. A wheel installs this package
and its entry point without root launchers, tests or user data.
The sdist includes the source, supporting scripts and bilingual documentation.

Settings live in the user profile, never in site-packages. If the new file is
absent, a source checkout reads the old portable settings file. Only known fields
with expected types are accepted. Saving creates the configuration directory and
replaces the target file through a temporary file in the same directory.

The test fixture controls Git's child environment without mutating Tcl's native
process environment. All repositories and remotes used by tests are temporary.
