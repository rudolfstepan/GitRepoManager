# User guide

[Documentation](../README.md) · [Deutsch](../de/user-guide.md)

## Launch and scan folder

Use Python 3.10+, Tkinter and Git on your PATH. The Windows Python installer
offers Tcl/Tk; Linux distributions may provide it as a separate system package.
No pip packages are required to run the source tree.

Run `python app.py`, double-click `start.bat` on Windows, or use `sh start.sh`
on Linux/macOS. An explicit folder, such as `python app.py "path/to/projects"`,
overrides the saved folder. Otherwise the last folder is used, followed by the
checkout's parent folder (or the current directory for an installed package).

The labels below are German because the current UI is German.

## Find and select repositories

1. Set **Suchordner** or use **Ordner wählen**.
2. Click **Repos suchen** for a recursive scan.
3. Check repositories in the first column. **Sichtbare auswählen** checks all
   visible rows; the checkbox in the header toggles all visible rows.
4. **Auswahl aufheben** clears the entire selection.

The selected row controls branch details. Checkboxes determine which repositories
receive Git actions. Checkbox selection is remembered across launches.

Search matches project names, paths, remotes and all known branch names. All
space-separated search terms must match. Column headings sort the list.
**Nur Auswahl** shows checked repositories. **Nur Änderungen** includes local
changes, ahead/behind commits and read errors.

Filters do not clear checkboxes. Actions apply to **all checked repositories,
including filtered-out rows**. The counter shows hidden checked repositories.

The scan includes nested repositories, submodules with a `.git` file, linked
worktrees and bare repositories. Directory links and Git-internal directories
are skipped. The optional dependency filter excludes `node_modules`, `.venv`,
`venv`, `__pycache__`, `.tox` and `.mypy_cache`; it is off by default.

## Branches and status

The main list shows the active branch, working-tree status, remotes and results.
**↑** counts local commits ahead of the upstream; **↓** counts commits behind it.
A dash means there is no upstream status to display.

Click a row to inspect local and remote-tracking branches below. A star marks
the active branch. Upstreams and tracking differences are also shown.
Switching, creating and deleting branches is done through Git in the terminal.

Remote branches and counts reflect the **last fetch**. Run Fetch for current
server data. Startup scans and local refreshes do not contact a server.

## Batch operations

Repositories are processed sequentially. Status is read again before each
operation. A failure does not prevent the remaining selection from being
processed. The UI stays responsive; checkboxes are locked during an action.

| Button | Behavior |
| --- | --- |
| **Fetch** | `git fetch --all --prune`: fetch all remotes and remove obsolete remote-tracking refs. |
| **Pull (ff-only)** | `git pull --ff-only --no-rebase --no-autostash`: update the active branch; skip any dirty working tree. |
| **Push** | Explicit local-branch-to-upstream refspec; force, mirror, automatic tag following and recursive submodule push are disabled for the call. |
| **Status aktualisieren** | Re-read all discovered repositories locally. |
| **Repos suchen** | Scan again to discover new or moved repositories. |

Push targets the configured upstream remote and branch. It does not use a
different `pushRemote`, `remote.pushDefault` or matching refspec. Configure a
remote upstream in your normal Git workflow first; the app does not create one.

Pull and Push require a local branch with a commit and remote upstream.
Bare repositories support Fetch only. The app does not create commits or stashes.

**Abbrechen** stops processing and prevents queued operations from starting.
Completed or transmitted changes remain; cancellation is not a rollback.
Network actions time out after five minutes per repository. Local Git reads
have a 45-second limit per command.

## Results, navigation and shortcuts

**Letzte Aktion** shows each repository's latest result.
**Aktivität & Ergebnisse** contains commands, output and totals; **Speichern**
exports the log. The widget retains approximately 12,000 lines.

**Ordner öffnen**, **Terminal öffnen** and **Pfad kopieren** act on the selected
row. The context menu offers the same functions. Double-click a project name
to open its folder.

| Shortcut | Action |
| --- | --- |
| F5 | Refresh local status |
| Ctrl+F | Focus search |
| Space | Toggle the selected row's checkbox when the list has focus |
| Ctrl+A | Check all visible repositories when the list has focus |
| Escape | Cancel current processing |

## Settings

The scan folder, window geometry, checkbox selection and dependency-filter
preference are saved in the user profile.

| Platform | File |
| --- | --- |
| Windows | `%APPDATA%\GitRepoManager\state.json` |
| macOS | `~/Library/Application Support/GitRepoManager/state.json` |
| Linux | `$XDG_CONFIG_HOME/git-repo-manager/state.json`, or `~/.config/git-repo-manager/state.json` |

If no new settings file exists, a checkout reads the previous
`.git-repo-manager.json` in the project root. Saving writes the new file and
leaves the original intact. Settings are excluded from Git and distributions.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Git missing | Install Git and restart the app to pick up PATH changes. |
| Tkinter or `init.tcl` error | Try `python -m tkinter` with the same interpreter; repair its Tcl/Tk component if needed. |
| Authentication failure | Authenticate with Git in a terminal or configure the SSH agent, then retry. |
| Missing upstream | Configure a tracking branch in your normal Git workflow. |
| Pull skipped | Commit or stash local changes yourself before retrying. |
| Pull rejected | Resolve diverging branches in Git before another fast-forward-only pull. |
| Dubious ownership | Review the repository owner and Git's message; ownership checks remain enabled. |
| Slow scan | Narrow the folder or enable dependency-directory skipping. |

Git terminal prompts and interactive Git Credential Manager prompts are disabled
during batch operations. Existing Git/SSH configuration and credentials are
used. Hooks and Git helpers retain their normal behavior; the app is not an
isolation environment for untrusted repositories.
