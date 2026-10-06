# Git Repo Manager

[English](README.md) · [Deutsch](README.de.md)

A lightweight desktop app for managing many local Git projects from one window.
Find repositories recursively, select them with checkboxes, inspect branches and
run Fetch, Pull or Push for the selection.

**Python 3.10+ · Tkinter · Git · MIT license · No third-party runtime packages**

The current user interface is in **German**. Documentation is available in
English and German. Windows is the primary desktop platform.

## Features

- Recursive discovery of normal and nested repositories, submodules, linked
  worktrees and bare repositories.
- Search by project, path, remote or branch; sortable columns and selection filters.
- Current branch, local and known remote branches, working-tree changes and
  ahead/behind counts.
- Batch Fetch, fast-forward-only Pull and Push to each current branch's upstream.
- Background processing, cancellation, per-repository results and an exportable log.
- Open a project folder or terminal directly from the list.
- Saved window size, scan folder and checkbox selection.

## Quick start

Install Python with Tkinter and Git, and make Git available on your PATH.
Download or clone this project, then run from the project folder:

```shell
python app.py
```

On Windows, double-click **[start.bat](start.bat)**.
On Linux or macOS, use `python3 app.py` or `sh start.sh`.

To choose the scan folder explicitly:

```shell
python app.py "D:\Development"
```

When launched from a source checkout, the first scan starts in the **parent of
the project folder**. The last chosen folder is remembered. No package installation
is needed for this start method.

Select repositories with the checkboxes, then click **Fetch**, **Pull (ff-only)**
or **Push**. Selecting a row displays its branches in the lower pane.

## Git behavior

| Action | Behavior |
| --- | --- |
| Fetch | Fetch all remotes and prune obsolete remote-tracking refs. |
| Pull | Fast-forward only; skip repositories with local changes. |
| Push | Push the active local branch to its configured upstream remote and branch. No force-push or automatic publishing of other branches/tags. |
| Refresh | Read local status again; no network request. |

Actions apply to **all checked repositories, including filtered-out rows**.
The UI displays the number of hidden checked repositories.

Remote branches and ahead/behind counts reflect the **last fetch**. Fetch first
to see changes from a server. Authentication uses your existing Git credentials
or SSH agent. See the [user guide](docs/en/user-guide.md) for details and shortcuts.

## Optional package installation

To install the checked-out project into a virtual environment:

```shell
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m git_repo_manager
```

On Linux/macOS, use `.venv/bin/python` instead. Installation also provides the
`git-repo-manager` desktop command in the environment's scripts directory.
An installed package defaults to the current working directory on its first run.

This documentation describes installation **from this source tree**; it does not
assume a published package on PyPI.

## Project structure

```text
GitRepoManager/
├── src/git_repo_manager/    # Application package
│   ├── gui.py              # Tkinter interface and background jobs
│   ├── git_backend.py      # Discovery, status and Git operations
│   ├── settings.py         # User settings and legacy migration
│   └── windows_job.py      # Windows subprocess cancellation
├── tests/                  # Backend, GUI and settings tests
├── scripts/                # Test runner and documentation checks
├── docs/
│   ├── en/                 # English guides
│   └── de/                 # Deutsche Anleitungen
├── .github/                # CI, issue forms and PR template
├── app.py                  # Run directly from a source checkout
├── start.bat / start.sh    # Desktop/source launchers
├── pyproject.toml          # Package metadata and build configuration
├── README.md / README.de.md
├── CONTRIBUTING.md / CONTRIBUTING.de.md
├── CHANGELOG.md
└── LICENSE
```

## Development and checks

Tests use temporary local repositories and bare remotes. They do not modify your
projects or contact external Git servers.

```shell
python scripts/test.py                  # All tests; graphical session required
python scripts/test.py --backend-only   # Git and settings; no display required
python scripts/test.py --gui-only       # Tkinter integration
python scripts/check_docs.py
```

The GitHub workflow is configured for backend tests on Windows and Linux with
Python 3.10 and 3.13, Windows GUI tests, and a package build check. This is a CI
configuration, not a claim that those remote jobs have already run.

Local verification was performed on Windows with Python 3.12. Linux/macOS desktop
behavior has not been manually validated.

## Documentation and contributions

- [Documentation index](docs/README.md)
- [User guide](docs/en/user-guide.md)
- [Development, packaging and release procedure](docs/en/development.md)
- [Architecture](docs/en/architecture.md)
- [Contributing](CONTRIBUTING.md) · [Change log](CHANGELOG.md)

Bug reports, pull requests and documentation improvements are welcome in English
or German. The project is licensed under the [MIT License](LICENSE).
