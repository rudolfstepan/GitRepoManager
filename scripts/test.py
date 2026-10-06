"""Run source-tree tests with separate backend and GUI interpreters."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--backend-only", action="store_true", help="Git and settings checks; no display required")
    group.add_argument("--gui-only", action="store_true", help="Tk integration test; graphical session required")
    args = parser.parse_args()
    suites = []
    if not args.gui_only:
        suites.append(["tests.test_backend", "tests.test_settings"])
    if not args.backend_only:
        suites.append(["tests.test_gui"])
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH")]))
    # Give Tcl its paths at process startup. The GUI suite is independent of
    # environment changes performed by Git integration fixtures.
    if os.name == "nt":
        for variable, folder in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
            library = Path(sys.base_prefix) / "tcl" / folder
            if library.is_dir():
                env.setdefault(variable, library.as_posix())
    for suite in suites:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "-v", *suite], cwd=ROOT, env=env,
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
