"""Read-only, asynchronous local change browser."""
import queue
import threading
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .git_backend import read_local_changes, read_change_diff


class ChangesView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.path = None
        self.generation = 0
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.changes = []
        self.closed = False
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 6))
        self.title = ttk.Label(header, text="Projekt in der Liste auswählen.", style="Section.TLabel")
        self.title.pack(anchor="w", fill="x")
        header.bind("<Configure>", lambda e: self.title.configure(wraplength=max(180, e.width - 12)))
        self.reload_button = ttk.Button(header, text="Änderungen neu laden", command=self.refresh, state="disabled")
        self.reload_button.pack(anchor="w", pady=(4, 0))
        split = ttk.Panedwindow(self, orient="vertical")
        split.pack(fill="both", expand=True)
        files = ttk.Frame(split)
        split.add(files, weight=1)
        self.files = ttk.Treeview(files, columns=("area", "status", "path"), show="headings",
                                  height=4, selectmode="browse")
        for name, label, width in (("area", "Bereich", 140), ("status", "Änderung", 110),
                                   ("path", "Datei", 260)):
            self.files.heading(name, text=label)
            self.files.column(name, width=width, minwidth=70)
        scroll = ttk.Scrollbar(files, command=self.files.yview)
        horizontal = ttk.Scrollbar(files, orient="horizontal", command=self.files.xview)
        self.files.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        self.files.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        files.rowconfigure(0, weight=1)
        files.columnconfigure(0, weight=1)
        self.files.tag_configure("Vorgemerkt", foreground="#166534")
        self.files.tag_configure("Nicht vorgemerkt", foreground="#92400e")
        self.files.tag_configure("Neu", foreground="#0369a1")
        self.files.tag_configure("Konflikt", foreground="#b91c1c")
        self.files.bind("<<TreeviewSelect>>", self._select)
        self.preview = ScrolledText(split, height=5, width=45, wrap="word", state="disabled",
                                    background="#ffffff", foreground="#1e293b", relief="flat",
                                    font=("Consolas", 10), padx=10, pady=8,
                                    selectbackground="#0f766e", selectforeground="white")
        split.add(self.preview, weight=3)
        self.preview.tag_configure("add", background="#dcfce7", foreground="#166534")
        self.preview.tag_configure("remove", background="#fee2e2", foreground="#991b1b")
        self.preview.tag_configure("header", foreground="#0369a1")
        self._show("Datei auswählen, um ihre Änderungen zu sehen.\nGrün / +: hinzugefügt · Rot / −: entfernt")
        self.timer = self.after(80, self._poll)
        self.bind("<Destroy>", self._destroy, add=True)

    def _destroy(self, event):
        if event.widget is self:
            self.closed = True
            self.cancel.set()
            self.after_cancel(self.timer)

    def set_repository(self, repo):
        path = repo.path if repo and not repo.bare else None
        if path == self.path:
            return
        self.path = path
        self.refresh()

    def _run(self, kind, work):
        self.cancel.set()
        self.cancel = threading.Event()
        cancel = self.cancel
        self.generation += 1
        generation = self.generation
        def job():
            try:
                value = work(cancel)
                self.events.put((generation, kind, value))
            except Exception as exc:
                self.events.put((generation, "error", str(exc)))
        threading.Thread(target=job, daemon=True, name="local-changes").start()

    def refresh(self):
        self.cancel.set()
        self.generation += 1
        self.changes = []
        self.files.delete(*self.files.get_children())
        self.reload_button.configure(state="normal" if self.path else "disabled")
        if self.path is None:
            self.title.configure(text="Projekt mit Arbeitsverzeichnis auswählen.")
            self._show("Keine Datei ausgewählt.")
            return
        path = self.path
        self.title.configure(text=f"{path.name} · Änderungen werden geladen …")
        self._show("Lokale Änderungen werden gelesen …")
        self._run("files", lambda cancel: read_local_changes(path, cancel))

    def _select(self, _event=None):
        selected = self.files.selection()
        if not selected or self.path is None:
            return
        change = self.changes[int(selected[0])]
        path = self.path
        self._show(f"{change.path}\nVorschau wird geladen …")
        self._run("diff", lambda cancel: read_change_diff(path, change, cancel))

    def _show(self, text):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        for line in text.splitlines(keepends=True):
            tag = ("header" if line.startswith(("+++", "---", "@@", "diff ")) else
                   "add" if line.startswith("+") else "remove" if line.startswith("-") else "")
            self.preview.insert("end", line, tag)
        self.preview.configure(state="disabled")
        self.preview.yview_moveto(0)

    def _poll(self):
        while True:
            try:
                generation, kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            if kind == "files":
                self.changes = value
                self.title.configure(text=f"{self.path.name} · {len({c.path for c in value})} nicht committete Dateien")
                for index, change in enumerate(value):
                    name = f"{change.original_path} → {change.path}" if change.original_path else change.path
                    self.files.insert("", "end", iid=str(index),
                                      values=(change.area, change.status, name), tags=(change.area,))
                self._show("Datei auswählen, um den Diff zu sehen.\nVorgemerkt = für den nächsten Commit im Index."
                           if value else "Keine lokalen Änderungen. Das Arbeitsverzeichnis ist sauber.")
                if value:
                    self.files.selection_set("0")
            else:
                self._show(("Änderungen konnten nicht geladen werden:\n" if kind == "error" else "") + value)
        if not self.closed:
            self.timer = self.after(80, self._poll)
