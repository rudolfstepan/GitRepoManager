# Development, packaging and releases

[Documentation](../README.md) · [Deutsch](../de/development.md)

## Work from the checkout

Python 3.10+ and Git are required. Tkinter and a graphical session are required
for the GUI. Runtime code uses only the Python standard library.

```shell
python app.py
python app.py --version
python scripts/test.py
python scripts/check_docs.py
```

The source launcher and test runner add the local `src/` directory themselves.
The installed module is started with `python -m git_repo_manager`.
Do not run `src/git_repo_manager/gui.py` directly; its imports belong to a package.

## Editable environment

Create a virtual environment and use its interpreter explicitly:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m git_repo_manager
```

On Linux/macOS replace `.venv\Scripts\python` with `.venv/bin/python`.
The optional `dev` extra provides build and metadata-validation tools; it is not
required to run the app or its unittest checks.

## Tests

```shell
python scripts/test.py
python scripts/test.py --backend-only
python scripts/test.py --gui-only
python scripts/check_docs.py
```

Backend and settings tests use no display. GUI tests use real Tk widgets and
require a graphical session; on a Linux CI host they can run under Xvfb.
The runner uses separate interpreters for backend and GUI checks.

Integration fixtures create temporary repositories, a local bare remote and
clones. Git child-process environments isolate the user's global/system config
and supply test-only author data. They exercise discovery, branches, push/fetch/
pull, divergence, cancellation, timeouts and configuration migration. GUI checks
cover selection, filtering, branch details and batch operations.

No external remote is contacted by the tests. Never substitute a personal
repository for the temporary fixtures.

The GitHub workflow configures Windows/Linux backend checks on Python 3.10 and
3.13, Windows GUI checks and a distribution build. It does not publish packages.
Remote CI status becomes available after the project is pushed to a GitHub repository.

## Build distributions

With the development tools installed, run from the project root:

```shell
python -m build
python -m twine check dist/*
```

This creates an sdist and a wheel in `dist/`. The wheel contains only the runtime
package and metadata. The source archive also includes both READMEs, guides,
tests, launchers and contribution documents. Local state, credentials, virtual
environments and build caches are excluded.

An offline wheel build is possible when a suitable setuptools version is already
installed:

```shell
python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist .
```

Test the wheel in a fresh environment outside the source import path:

```shell
python -m venv .verify/venv
# Windows; replace the interpreter path on other platforms:
.verify\venv\Scripts\python -m pip install --no-deps dist/git_repo_manager-0.1.0-py3-none-any.whl
.verify\venv\Scripts\python -m git_repo_manager --version
```

Use the filename matching the current version. The package metadata follows the
[Python packaging guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).

## Release procedure

1. Update `__version__` in `src/git_repo_manager/__init__.py`. Package metadata
   reads this value; do not introduce a second version source.
2. Update both documentation trees and the bilingual change log.
3. Run tests, documentation checks and the package build.
4. Install the wheel in a clean environment and check the desktop launch.
5. Date the change-log entry, commit the reviewed files and create a version tag.
6. When a remote and release destination have been chosen, publish the tag and
   release artifacts deliberately.

No remote URL, automatic publishing credentials or deployment workflow is embedded
in this project. Before a hosted release, add the actual repository/documentation
URLs to package metadata so links on the chosen package index resolve correctly.
