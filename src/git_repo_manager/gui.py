"""Bulk Git UI. Python 3.10+ and Tkinter; no third-party packages."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
# Tcl reads the process environment when its DLL is first loaded.
if os.name == "nt":
    for variable, folder in (("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")):
        library = Path(sys.base_prefix) / "tcl" / folder
        if library.is_dir():
            os.environ.setdefault(variable, library.as_posix())

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from .git_backend import ACTIONS, Repository, discover_repositories, read_repository, run_action
from .changes_view import ChangesView

from . import __version__
from .settings import default_scan_root, default_state_file, legacy_state_file, load_state, save_state
BG, PANEL, TEXT, MUTED, ACCENT = "#f1f5f9", "#ffffff", "#1e293b", "#475569", "#0f766e"


def path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


class GitRepoManager(tk.Tk):
    def __init__(self, root_path: Path | None = None, *, auto_scan: bool = True,
                 state_file: Path | None = None):

        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                pass
        # Initialize Tcl before loading Tk (also works with Windows pythonw).
        super().__init__(useTk=False)
        self.loadtk()
        self.state_file = state_file if state_file is not None else default_state_file()
        self.legacy_state_file = legacy_state_file() if state_file is None else None
        state = self._read_state()
        self.title("Git Repo Manager")
        self.configure(bg=BG)
        self.ui_scale = max(1.0, float(self.tk.call("tk", "scaling")) / (96 / 72))
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(round(1380 * self.ui_scale), screen_w - 80)
        height = min(round(900 * self.ui_scale), screen_h - 100)
        self.minsize(min(round(1080 * self.ui_scale), width), min(round(700 * self.ui_scale), height))
        default_geometry = f"{width}x{height}"
        try:
            self.geometry(state.get("geometry", default_geometry))
        except tk.TclError:
            self.geometry(default_geometry)
        self.repos: dict[str, Repository] = {}
        self.checked = set(state.get("checked", []))
        self.results: dict[str, str] = {}
        self.events: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.worker: threading.Thread | None = None
        self.busy = ""
        self.closing = False
        self.sort_column, self.sort_reverse = "name", False
        self.root_path = tk.StringVar(value=str(root_path or state.get("root") or default_scan_root()))
        self.search = tk.StringVar()
        self.only_dirty = tk.BooleanVar()
        self.only_checked = tk.BooleanVar()
        self.skip_dependencies = tk.BooleanVar(value=bool(state.get("skip_dependencies", False)))
        self.recursive_search = tk.BooleanVar(value=bool(state.get("recursive_search", False)))
        self.status_text = tk.StringVar(value="Bereit.")
        self.stats_text = tk.StringVar(value="Noch keine Repositories geladen")
        self.selection_text = tk.StringVar(value="Projekte links anhaken, um eine Aktion auszuführen.")
        self.active_project_text = tk.StringVar(value="Projekt auswählen")
        self.detail_title = tk.StringVar(value="Repository markieren, um Branches zu sehen")
        self.detail_info = tk.StringVar(value="Lokale und zuletzt abgerufene Remote-Branches erscheinen hier.")
        self._style()
        self._build_ui()
        self.search.trace_add("write", lambda *_: self._render())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<F5>", lambda _: self.refresh())
        self.bind("<Control-f>", self._focus_search)
        self.bind("<Control-a>", self._keyboard_select_all)
        self.bind("<Escape>", lambda _: self.stop() if self.busy else None)
        self.after(80, self._drain_events)
        self._log("Bereit. Die Suche liest ausschließlich lokale Git-Daten.")
        self._log("↑/↓ und Remote-Branches entsprechen dem letzten Fetch. Fetch aktualisiert diese Daten.")
        if not shutil.which("git"):
            self.after(100, lambda: messagebox.showerror("Git fehlt", "Git wurde nicht im PATH gefunden. Bitte Git installieren und die Anwendung neu starten."))
            self.status_text.set("Git fehlt im PATH.")
        elif auto_scan:
            self.after(150, self.scan)
        self._update_controls()

    def _read_state(self) -> dict:
        return load_state(self.state_file, fallback=self.legacy_state_file)

    def _save_state(self) -> None:
        state = {"root": self.root_path.get(), "geometry": self.geometry(),
                 "recursive_search": self.recursive_search.get(),
                 "skip_dependencies": self.skip_dependencies.get(), "checked": sorted(self.checked)}
        try:
            save_state(self.state_file, state)
        except OSError as exc:
            self._log(f"Einstellungen konnten nicht gespeichert werden: {exc}", "error")

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", foreground=MUTED)
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=(12, 7), background="#e5eaf3", borderwidth=0)
        style.map("TButton", background=[("active", "#d9e2f2"), ("disabled", "#eceff5")],
                  foreground=[("disabled", "#96a0b1")])
        style.configure("Accent.TButton", background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", "#115e59"), ("disabled", "#cbd5e1")],
                  foreground=[("disabled", "#f3f5fa")])
        style.configure("TEntry", padding=7, fieldbackground=PANEL)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=round(31 * self.ui_scale), borderwidth=0)
        style.configure("Treeview.Heading", background="#e6ecf5", foreground=TEXT,
                        padding=(7, 8), font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 7), background="#e2e8f0", foreground=MUTED)
        style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
        style.configure("TCheckbutton", padding=4)
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#e1e8f3", borderwidth=0)
        style.configure("TPanedwindow", background=BG)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(22, 18, 22, 12))
        outer.pack(fill="both", expand=True)
        location = ttk.Frame(outer)
        location.pack(fill="x")
        ttk.Label(location, text="Suchordner").pack(side="left", padx=(0, 12))
        self.root_entry = ttk.Entry(location, textvariable=self.root_path)
        self.root_entry.pack(side="left", fill="x", expand=True)
        self.root_entry.bind("<Return>", lambda _: self.scan())
        self.browse_button = ttk.Button(location, text="Ordner wählen", command=self._browse)
        self.browse_button.pack(side="left", padx=(8, 0))
        self.scan_button = ttk.Button(location, text="Repos suchen", style="Accent.TButton", command=self.scan)
        self.scan_button.pack(side="left", padx=(8, 0))
        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(5, 10))
        self.skip_box = ttk.Checkbutton(options, text="Abhängigkeiten überspringen (node_modules, .venv, …)",
                                       variable=self.skip_dependencies)
        self.recursive_search_box = ttk.Checkbutton(
            options, text="Rekursive Suche",
            variable=self.recursive_search)
        self.recursive_search_box.pack(side="left")
        self.skip_box.pack(side="left", padx=(18, 0))
        ttk.Separator(outer).pack(fill="x", pady=(0, 10))
        searchbar = ttk.Frame(outer)
        searchbar.pack(fill="x", pady=(0, 10))
        ttk.Label(searchbar, text="Projekte filtern").pack(side="left", padx=(0, 12))
        self.search_entry = ttk.Entry(searchbar, textvariable=self.search)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(searchbar, text="Filter löschen", command=self._clear_filters).pack(side="left", padx=(4, 12))
        ttk.Checkbutton(searchbar, text="Nur Änderungen", variable=self.only_dirty,
                        command=self._render).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(searchbar, text="Nur Auswahl", variable=self.only_checked,
                        command=self._render).pack(side="left")
        selection = ttk.Frame(outer)
        selection.pack(fill="x", pady=(0, 8))
        ttk.Label(selection, textvariable=self.stats_text, style="Section.TLabel").pack(side="left")
        self.clear_button = ttk.Button(selection, text="Auswahl aufheben", command=self.clear_checks)
        self.clear_button.pack(side="right")
        self.select_button = ttk.Button(selection, text="Sichtbare auswählen", command=self.check_visible)
        self.select_button.pack(side="right", padx=7)
        actions = ttk.Frame(outer, padding=(0, 8))
        actions.pack(side="bottom", fill="x")
        ttk.Label(actions, textvariable=self.selection_text, style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        action_row = ttk.Frame(actions)
        action_row.pack(fill="x")
        self.action_buttons = {}
        for action, label in (("fetch", "Fetch für angehakte"),
                              ("pull", "Pull für angehakte"),
                              ("push", "Push für angehakte")):
            button = ttk.Button(action_row, text=label, command=lambda a=action: self.perform(a))
            button.pack(side="left", padx=(0, 7))
            self.action_buttons[action] = button
        self.refresh_button = ttk.Button(action_row, text="Status neu laden · F5", command=self.refresh)
        self.refresh_button.pack(side="right")
        panes = ttk.Panedwindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True)
        listing = ttk.Frame(panes)
        panes.add(listing, weight=1)
        columns = ("check", "name", "branch", "status", "sync", "remotes", "result", "path")
        self.tree = ttk.Treeview(listing, columns=columns, show="headings", selectmode="browse",
                                displaycolumns=("check", "name", "status"))
        headings = {"check": "☐", "name": "Projekt", "branch": "Branch",
                    "status": "Status", "sync": "↑ Senden / ↓ Holen", "remotes": "Remotes",
                    "result": "Letzte Aktion", "path": "Pfad"}
        widths = {"check": 36, "name": 190, "branch": 155, "status": 115,
                  "sync": 150, "remotes": 100, "result": 160, "path": 260}
        for col in columns:
            self.tree.heading(col, text=headings[col],
                              command=self._toggle_all if col == "check" else lambda c=col: self._sort(c))
            self.tree.column(col, width=round(widths[col] * self.ui_scale), minwidth=round((widths[col] if col == "check" else 65) * self.ui_scale),
                             stretch=col in ("name", "path"), anchor="center" if col in ("check", "sync") else "w")
        yscroll = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(listing, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        listing.rowconfigure(0, weight=1)
        listing.columnconfigure(0, weight=1)
        self.empty_label = ttk.Label(listing, text="Mit »Repos suchen« Projekte in diesem Ordner finden.",
                                     style="Muted.TLabel", anchor="center", justify="center")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.tree.tag_configure("error", foreground="#b42332")
        self.tree.tag_configure("dirty", foreground="#8b5605")
        self.tree.tag_configure("even", background="#f7f9fd")
        self.tree.bind("<Button-1>", self._tree_click)
        self.tree.bind("<space>", self._tree_space)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._details())
        self.tree.bind("<Double-1>", self._double_click)
        self.tree.bind("<Button-3>", self._context_menu)
        workspace = ttk.Frame(panes, padding=(12, 0, 0, 0))
        panes.add(workspace, weight=3)
        project_header = ttk.Label(workspace, textvariable=self.active_project_text,
                                   style="Section.TLabel", wraplength=600)
        project_header.pack(anchor="w", fill="x", pady=(0, 6))
        workspace.bind("<Configure>", lambda e: project_header.configure(wraplength=max(200, e.width - 24)))
        project_actions = ttk.Frame(workspace)
        project_actions.pack(fill="x", pady=(0, 8))
        self.project_action_buttons = {}
        for action, label in (("fetch", "Fetch · Abrufen"), ("pull", "Pull · Übernehmen"),
                              ("push", "Push · Senden")):
            button = ttk.Button(project_actions, text=label,
                                command=lambda a=action: self.perform(a, selected_only=True))
            button.pack(side="left", padx=(0, 5))
            self.project_action_buttons[action] = button
        self.detail_tabs = ttk.Notebook(workspace)
        self.detail_tabs.pack(fill="both", expand=True)
        def initial_split(event):
            if event.width > 100:
                panes.sashpos(0, round(event.width * 0.34))
                panes.unbind("<Configure>")
        panes.bind("<Configure>", initial_split)
        self.changes_view = ChangesView(self.detail_tabs)
        self.detail_tabs.add(self.changes_view, text="Lokale Änderungen")
        detail = ttk.Frame(self.detail_tabs, padding=(8, 8))
        self.detail_tabs.add(detail, text="Projekt & Branches")
        ttk.Label(detail, textvariable=self.detail_title, style="Section.TLabel").pack(anchor="w")
        self.detail_label = ttk.Label(detail, textvariable=self.detail_info, style="Muted.TLabel",
                                      wraplength=560, justify="left")
        self.detail_label.pack(anchor="w", fill="x", pady=(5, 8))
        detail.bind("<Configure>", lambda e: self.detail_label.configure(wraplength=max(220, e.width - 20)))
        branch_frame = ttk.Frame(detail)
        branch_frame.pack(fill="both", expand=True)
        self.branch_tree = ttk.Treeview(branch_frame, columns=("kind", "branch", "upstream", "tracking"),
                                       show="headings", height=4, selectmode="browse")
        for col, title, width in (("kind", "Typ", 85), ("branch", "Branch", 200),
                                  ("upstream", "Upstream", 170), ("tracking", "Stand", 105)):
            self.branch_tree.heading(col, text=title)
            self.branch_tree.column(col, width=round(width * self.ui_scale), minwidth=60, stretch=True)
        branch_y = ttk.Scrollbar(branch_frame, orient="vertical", command=self.branch_tree.yview)
        branch_x = ttk.Scrollbar(branch_frame, orient="horizontal", command=self.branch_tree.xview)
        self.branch_tree.configure(yscrollcommand=branch_y.set, xscrollcommand=branch_x.set)
        self.branch_tree.grid(row=0, column=0, sticky="nsew")
        branch_y.grid(row=0, column=1, sticky="ns")
        branch_x.grid(row=1, column=0, sticky="ew")
        branch_frame.rowconfigure(0, weight=1)
        branch_frame.columnconfigure(0, weight=1)
        self.branch_tree.tag_configure("current", foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        detail_buttons = ttk.Frame(detail)
        detail_buttons.pack(side="bottom", fill="x", pady=(8, 0), before=branch_frame)
        ttk.Button(detail_buttons, text="Ordner öffnen", command=self.open_folder).pack(side="left")
        ttk.Button(detail_buttons, text="Terminal öffnen", command=self.open_terminal).pack(side="left", padx=7)
        ttk.Button(detail_buttons, text="Pfad kopieren", command=self.copy_path).pack(side="left")
        activity = ttk.Frame(self.detail_tabs, padding=(8, 8))
        self.detail_tabs.add(activity, text="Protokoll")
        log_header = ttk.Frame(activity)
        log_header.pack(fill="x", pady=(0, 7))
        ttk.Label(log_header, text="Aktivität & Ergebnisse", style="Section.TLabel").pack(side="left")
        ttk.Button(log_header, text="Speichern", command=self.save_log).pack(side="right")
        self.log = ScrolledText(activity, height=8, width=52, wrap="word", state="disabled", relief="flat",
                                borderwidth=0, padx=12, pady=10, font=("Consolas", 9),
                                background=PANEL, foreground=TEXT, insertbackground=TEXT)
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("error", foreground="#b91c1c")
        self.log.tag_config("success", foreground="#166534")
        self.log.tag_config("muted", foreground=MUTED)
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(12, 0), before=panes)
        self.progress = ttk.Progressbar(footer, length=140, mode="indeterminate")
        self.progress.pack(side="right", padx=(12, 0))
        self.stop_button = ttk.Button(footer, text="Abbrechen", command=self.stop)
        self.stop_button.pack(side="right", padx=(8, 0))
        ttk.Label(footer, textvariable=self.status_text, style="Muted.TLabel",
                  anchor="w").pack(side="left", fill="x", expand=True)
        self.menu = tk.Menu(self, tearoff=False, font=("Segoe UI", 10))
        self.menu.add_command(label="Checkbox umschalten", command=self._toggle_focused)
        self.menu.add_separator()
        self.menu.add_command(label="Ordner öffnen", command=self.open_folder)
        self.menu.add_command(label="Terminal öffnen", command=self.open_terminal)
        self.menu.add_command(label="Pfad kopieren", command=self.copy_path)


    def _focus_search(self, _event=None):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")
        return "break"

    def _clear_filters(self):
        self.only_dirty.set(False)
        self.only_checked.set(False)
        self.search.set("")

    def _keyboard_select_all(self, event):
        if event.widget is self.tree:
            self.check_visible()
            return "break"

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.root_path.get(), title="Suchordner wählen")
        if folder:
            self.root_path.set(folder)
            self.scan()

    def _log(self, message: str, tag: str = ""):
        self.log.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{timestamp}] {message}\n", tag)
        if int(self.log.index("end-1c").split(".")[0]) > 12000:
            self.log.delete("1.0", "2001.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start(self, mode: str, job):
        if self.busy:
            return
        self.busy = mode
        self.cancel = threading.Event()
        self.progress.start(12)
        self._update_controls()
        def guarded():
            try:
                job()
            except Exception:
                self.events.put(("log", traceback.format_exc(), "error"))
                self.events.put(("status", "Fehler – Details im Protokoll."))
                self.events.put(("cancel_pending",))
            finally:
                self.events.put(("done",))
        self.worker = threading.Thread(target=guarded, daemon=True, name="git-manager-worker")
        self.worker.start()

    def scan(self):
        if self.busy:
            return
        root = Path(self.root_path.get()).expanduser()
        if not root.is_dir():
            messagebox.showerror("Ordner nicht gefunden", f"Der Suchordner existiert nicht:\n{root}")
            return
        self.root_path.set(str(root.resolve()))
        self.repos.clear()
        self.results.clear()
        self._render()
        self._details()
        self._save_state()
        self._log(f"Suche unter {root} …")
        self.status_text.set("Repositories werden gesucht …")
        skip = self.skip_dependencies.get()
        recursive = self.recursive_search.get()
        def job():
            futures = []
            found = 0
            last_progress = 0.0
            def progress(count, folder):
                nonlocal last_progress
                now = time.monotonic()
                if now - last_progress > 0.3:
                    self.events.put(("status", f"Suche: {count:,} Ordner geprüft · {found} Repositories gefunden"))
                    last_progress = now
            def loaded(future):
                if not future.cancelled():
                    try:
                        repo = future.result()
                        if not self.cancel.is_set():
                            self.events.put(("repo", repo))
                    except Exception as exc:
                        self.events.put(("log", f"Statusabfrage fehlgeschlagen: {exc}", "error"))
            with ThreadPoolExecutor(max_workers=4, thread_name_prefix="git-status") as pool:
                for path in discover_repositories(
                    root, self.cancel, skip,
                    on_error=lambda text: self.events.put(("log", text, "error")),
                    on_progress=progress,
                    recursive=recursive,
                ):
                    found += 1
                    future = pool.submit(read_repository, path, self.cancel)
                    future.add_done_callback(loaded)
                    futures.append(future)
                if self.cancel.is_set():
                    for future in futures:
                        future.cancel()
            text = f"Suche {'abgebrochen' if self.cancel.is_set() else 'abgeschlossen'} · {found} Repositories gefunden."
            self.events.put(("status", text))
            self.events.put(("log", text, ""))
        self._start("scan", job)

    def refresh(self):
        if self.busy:
            return
        paths = [repo.path for repo in self.repos.values()]
        if not paths:
            self.scan()
            return
        self.status_text.set(f"Status für {len(paths)} Repositories wird aktualisiert …")
        def job():
            with ThreadPoolExecutor(max_workers=4) as pool:
                for repo in pool.map(lambda p: read_repository(p, self.cancel), paths):
                    if not self.cancel.is_set():
                        self.events.put(("repo", repo))
            self.events.put(("status", "Aktualisierung abgebrochen." if self.cancel.is_set()
                             else f"Status von {len(paths)} Repositories aktualisiert."))
        self._start("refresh", job)

    def perform(self, action: str, *, selected_only: bool = False):
        if self.busy:
            return
        if selected_only:
            repo = self._selected_repo()
            paths = [repo.path] if repo else []
        else:
            paths = [repo.path for key, repo in self.repos.items() if key in self.checked]
        if not paths:
            return
        label = ACTIONS[action]
        self._log(f"{label} gestartet · {len(paths)} ausgewählte Repositories")
        for path in paths:
            self.results[path_key(path)] = "Wartet …"
        self._render()
        def job():
            success = failures = skipped = completed = 0
            for index, path in enumerate(paths, 1):
                if self.cancel.is_set():
                    break
                key = path_key(path)
                self.events.put(("status", f"{label} · {index}/{len(paths)} · {path.name}"))
                self.events.put(("result", key, f"{label} läuft …"))
                self.events.put(("log", f"{label}: {path}", ""))
                fresh = read_repository(path, self.cancel)
                if self.cancel.is_set():
                    break
                result = run_action(fresh, action, self.cancel)
                completed += 1
                if result.args:
                    self.events.put(("log", subprocess.list2cmdline(result.args), "muted"))
                self.events.put(("log", result.output or "Erfolgreich abgeschlossen.",
                                 "success" if result.ok else ("muted" if result.skipped else "error")))
                if result.ok:
                    success += 1
                elif result.skipped:
                    skipped += 1
                else:
                    failures += 1
                state = "Abgebrochen" if result.cancelled else (f"{label} ✓" if result.ok else f"{label}: Fehler")
                if result.skipped:
                    state = f"Übersprungen: {result.output}"
                elif not result.ok and not result.cancelled and result.output:
                    state += f" · {result.output}"
                self.events.put(("result", key, state))
                if not self.cancel.is_set():
                    self.events.put(("repo", read_repository(path, self.cancel)))
            if self.cancel.is_set():
                self.events.put(("cancel_pending",))
            text = f"{label}: {success} erfolgreich · {skipped} übersprungen · {failures} fehlgeschlagen"
            if completed < len(paths):
                text += f" · {len(paths) - completed} nicht ausgeführt"
            self.events.put(("status", text))
            self.events.put(("log", text, ""))
        self._start("action", job)

    def stop(self):
        if self.busy:
            self.cancel.set()
            self.status_text.set("Abbruch läuft … Bereits abgeschlossene Git-Aktionen bleiben bestehen.")
            self.stop_button.configure(state="disabled")

    def _drain_events(self):
        changed = False
        for _ in range(120):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            kind, *values = event
            if kind == "repo":
                repo = values[0]
                key = path_key(repo.path)
                self.repos[key] = repo
                if repo.error:
                    self._log(f"{repo.path}: {repo.error}", "error")
                changed = True
            elif kind == "result":
                self.results[values[0]] = values[1]
                changed = True
            elif kind == "cancel_pending":
                for key, result in self.results.items():
                    if result == "Wartet …" or result.endswith("läuft …"):
                        self.results[key] = "Nicht ausgeführt / abgebrochen"
                changed = True
            elif kind == "log":
                self._log(*values)
            elif kind == "status":
                self.status_text.set(values[0])
            elif kind == "done":
                self.busy = ""
                self.progress.stop()
                self._save_state()
                self.changes_view.refresh()
                changed = True
        if changed:
            self._render()
            self._details()
        if self.closing and not self.busy:
            self.destroy()
            return
        self.after(80, self._drain_events)

    def _matches(self, key, repo):
        if self.only_checked.get() and key not in self.checked:
            return False
        if self.only_dirty.get() and not (repo.dirty or repo.ahead or repo.behind or repo.error):
            return False
        terms = self.search.get().casefold().split()
        haystack = " ".join([str(repo.path), repo.branch, repo.upstream, *repo.remotes,
                             *(branch.name for branch in repo.branches)]).casefold()
        return all(term in haystack for term in terms)

    def _sort(self, column):
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        self.sort_column = column
        self._render()

    def _sort_value(self, item):
        key, repo = item
        values = {"name": repo.path.name.casefold(), "branch": repo.branch.casefold(),
                  "status": repo.status.casefold(), "sync": (repo.ahead, repo.behind),
                  "remotes": " ".join(repo.remotes), "result": self.results.get(key, ""),
                  "path": str(repo.path).casefold()}
        return values.get(self.sort_column, str(repo.path).casefold()), str(repo.path).casefold()

    def _render(self):
        selected = self.tree.selection()
        visible = sorted(((key, repo) for key, repo in self.repos.items() if self._matches(key, repo)),
                         key=self._sort_value, reverse=self.sort_reverse)
        keys = {key for key, _ in visible}
        for key in self.tree.get_children():
            if key not in keys:
                self.tree.delete(key)
        for index, (key, repo) in enumerate(visible):
            result = self.results.get(key, "—")
            tags = ["even"] if index % 2 == 0 else []
            if repo.error or repo.conflicts or "Fehler" in result:
                tags.append("error")
            elif repo.dirty:
                tags.append("dirty")
            values = ("☑" if key in self.checked else "☐", repo.path.name, repo.branch or "—",
                      repo.status, f"↑{repo.ahead} ↓{repo.behind}" if repo.upstream else "—",
                      ", ".join(repo.remotes) or "—", result, str(repo.path))
            if self.tree.exists(key):
                self.tree.item(key, values=values, tags=tags)
                self.tree.move(key, "", index)
            else:
                self.tree.insert("", index, iid=key, values=values, tags=tags)
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        elif visible:
            self.tree.selection_set(visible[0][0])
        chosen = sum(key in self.checked for key in self.repos)
        hidden_checked = sum(key in self.checked and key not in keys for key in self.repos)
        extra = f" ({hidden_checked} ausgeblendet)" if hidden_checked else ""
        self.stats_text.set(f"{len(visible)} von {len(self.repos)} Projekten · {chosen} ausgewählt{extra}")
        self.selection_text.set(
            f"Sammelaktion für {chosen} angehakte Projekte{extra}"
            if chosen else "Mehrere Projekte bearbeiten: links anhaken, dann hier die Sammelaktion wählen.")
        if visible:
            self.empty_label.place_forget()
        else:
            text = ("Keine Projekte passen zum Filter.\nMit »Filter löschen« alle Projekte anzeigen."
                    if self.repos else "Keine Projekte angezeigt.\nSuchordner prüfen und »Repos suchen« anklicken.\n"
                    "Für tiefere Unterordner »Rekursive Suche« aktivieren.")
            if self.busy == "scan":
                text = "Projekte werden gesucht …"
            self.empty_label.configure(text=text)
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.tree.heading("check", text="☑" if keys and keys.issubset(self.checked) else "☐")
        self._update_controls()

    def _update_controls(self):
        idle = not self.busy
        selected = sum(key in self.checked for key in self.repos)
        for button in self.action_buttons.values():
            button.configure(state="normal" if idle and selected else "disabled")
        for button in self.project_action_buttons.values():
            button.configure(state="normal" if idle and self._selected_repo() else "disabled")
        for widget in (self.scan_button, self.browse_button, self.root_entry, self.skip_box,
                       self.recursive_search_box):
            widget.configure(state="normal" if idle else "disabled")
        self.refresh_button.configure(state="normal" if idle else "disabled")
        self.stop_button.configure(state="normal" if self.busy and not self.cancel.is_set() else "disabled")
        self.select_button.configure(state="normal" if idle and self.tree.get_children() else "disabled")
        self.clear_button.configure(state="normal" if idle and self.checked else "disabled")

    def _toggle(self, key):
        if self.busy == "action":
            return
        if key in self.checked:
            self.checked.remove(key)
        else:
            self.checked.add(key)
        self._render()

    def _toggle_focused(self):
        selection = self.tree.selection()
        if selection:
            self._toggle(selection[0])

    def _tree_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#1":
            key = self.tree.identify_row(event.y)
            if key:
                self.tree.selection_set(key)
                self.tree.focus(key)
                self.tree.focus_set()
                self._toggle(key)
                return "break"

    def _tree_space(self, _event):
        self._toggle_focused()
        return "break"

    def _double_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell" and self.tree.identify_column(event.x) != "#1":
            self.open_folder()

    def check_visible(self):
        if self.busy == "action":
            return
        self.checked.update(self.tree.get_children())
        self._render()

    def clear_checks(self):
        if self.busy == "action":
            return
        self.checked.clear()
        self._render()

    def _toggle_all(self):
        if self.busy == "action":
            return
        keys = set(self.tree.get_children())
        if keys and keys.issubset(self.checked):
            self.checked.difference_update(keys)
        else:
            self.checked.update(keys)
        self._render()

    def _selected_repo(self):
        selected = self.tree.selection()
        return self.repos.get(selected[0]) if selected else None

    def _details(self):
        children = self.branch_tree.get_children()
        if children:
            self.branch_tree.delete(*children)
        repo = self._selected_repo()
        self.changes_view.set_repository(repo)
        self._update_controls()
        if not repo:
            self.active_project_text.set("Projekt links anklicken · Änderungen erscheinen hier")
            self.detail_title.set("Repository markieren, um Branches zu sehen")
            self.detail_info.set("★ = aktueller Branch · Remote-Branches: Stand des letzten Fetch")
            return
        self.active_project_text.set(
            f"{repo.path.name} · {repo.branch or '—'}\n{repo.status} · "
            f"↑ {repo.ahead} zu senden · ↓ {repo.behind} zu holen")
        local = sum(not b.remote for b in repo.branches)
        remote = len(repo.branches) - local
        self.detail_title.set(f"{repo.path.name} · {local} lokale / {remote} Remote-Branches")
        self.detail_info.set(f"{repo.path}\nAktiv: {repo.branch or '—'}  ·  Upstream: {repo.upstream or '—'}"
                             + f"  ·  Remotes: {', '.join(repo.remotes) or '—'}"
                             + (f"\nLetzte Aktion: {self.results[path_key(repo.path)]}"
                                if path_key(repo.path) in self.results else "")
                             + (f"\n{repo.error}" if repo.error else "\nRemote-Branches: Stand des letzten Fetch"))
        for branch in sorted(repo.branches, key=lambda b: (b.remote, not b.current, b.name.casefold())):
            tracking = branch.tracking.replace("ahead ", "↑").replace("behind ", "↓").replace("gone", "entfernt").strip("[]")
            self.branch_tree.insert("", "end", values=("Remote" if branch.remote else "Lokal",
                ("★ " if branch.current else "") + branch.name, branch.upstream or "—",
                tracking or branch.commit), tags=("current",) if branch.current else ())

    def _context_menu(self, event):
        key = self.tree.identify_row(event.y)
        if key:
            self.tree.selection_set(key)
            self.tree.focus(key)
            self.menu.tk_popup(event.x_root, event.y_root)

    def open_folder(self):
        repo = self._selected_repo()
        if not repo:
            return
        try:
            if os.name == "nt":
                os.startfile(repo.path)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(repo.path)])
        except OSError as exc:
            messagebox.showerror("Ordner öffnen", str(exc))

    def open_terminal(self):
        repo = self._selected_repo()
        if not repo:
            return
        try:
            if os.name == "nt":
                subprocess.Popen(["powershell.exe", "-NoLogo", "-NoProfile", "-NoExit"],
                                 cwd=repo.path, creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal", str(repo.path)])
            else:
                subprocess.Popen(["x-terminal-emulator"], cwd=repo.path)
        except OSError as exc:
            messagebox.showerror("Terminal öffnen", str(exc))

    def copy_path(self):
        repo = self._selected_repo()
        if repo:
            self.clipboard_clear()
            self.clipboard_append(str(repo.path))
            self.status_text.set(f"Pfad kopiert: {repo.path}")

    def save_log(self):
        filename = filedialog.asksaveasfilename(title="Aktivitätsprotokoll speichern",
                    defaultextension=".txt", initialfile=f"git-log-{datetime.now():%Y%m%d-%H%M%S}.txt",
                    filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")])
        if filename:
            try:
                Path(filename).write_text(self.log.get("1.0", "end-1c"), encoding="utf-8")
                self.status_text.set(f"Protokoll gespeichert: {filename}")
            except OSError as exc:
                messagebox.showerror("Speichern fehlgeschlagen", str(exc))

    def _close(self):
        self._save_state()
        if self.busy:
            self.closing = True
            self.stop()
            self.title("Git Repo Manager – wird beendet …")
        else:
            self.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find Git repositories recursively and run batch Git actions."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("root", nargs="?", type=Path,
                        help="Folder to scan; defaults to the saved folder or workspace.")
    args = parser.parse_args(argv)
    app = GitRepoManager(args.root)
    app.mainloop()


if __name__ == "__main__":
    main()
