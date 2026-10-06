# Git Repo Manager

[English](README.md) · [Deutsch](README.de.md)

Eine kleine Desktop-Anwendung, mit der du viele lokale Git-Projekte in einem
Fenster verwaltest: Repositories rekursiv finden, per Checkbox auswählen, Branches
ansehen und Fetch, Pull oder Push gemeinsam ausführen.

**Python 3.10+ · Tkinter · Git · MIT-Lizenz · Keine zusätzlichen Laufzeitpakete**

Die Benutzeroberfläche ist derzeit **deutsch**. Die Dokumentation gibt es auf
Deutsch und Englisch. Windows ist die primäre Desktop-Plattform.

## Funktionen

- Rekursive Suche nach normalen und verschachtelten Repositories, Submodulen,
  verknüpften Worktrees und Bare-Repositories.
- Suche nach Projekt, Pfad, Remote oder Branch; sortierbare Spalten und Auswahlfilter.
- Aktiver Branch, lokale und bekannte Remote-Branches, lokale Änderungen und
  vorausliegende bzw. nachzuholende Commits.
- Gemeinsames Fetch, Pull ausschließlich per Fast-forward und Push zum Upstream.
- Hintergrundverarbeitung, Abbruch, Ergebnisse je Repository und exportierbares Protokoll.
- Projektordner und Terminal direkt aus der Liste öffnen.
- Gespeicherte Fenstergröße, Suchordner und Checkbox-Auswahl.

## Schnellstart

Python mit Tkinter und Git installieren; Git muss im PATH verfügbar sein.
Dieses Projekt herunterladen oder klonen und im Projektordner starten:

```shell
python app.py
```

Unter Windows genügt ein Doppelklick auf **[start.bat](start.bat)**.
Unter Linux oder macOS: `python3 app.py` oder `sh start.sh`.

Einen Suchordner ausdrücklich vorgeben:

```shell
python app.py "D:\Development"
```

Beim Start aus dem Quellcode beginnt die erste Suche im **übergeordneten Ordner
des Projekts**. Später wird der zuletzt gewählte Suchordner verwendet. Für diesen
Startweg ist keine Paketinstallation nötig.

Repositories links anhaken und **Fetch**, **Pull (ff-only)** oder **Push** anklicken.
Ein Klick auf eine Zeile zeigt deren Branches im unteren Bereich.

## Verhalten der Git-Aktionen

| Aktion | Verhalten |
| --- | --- |
| Fetch | Alle Remotes abrufen und veraltete Remote-Tracking-Refs entfernen. |
| Pull | Ausschließlich Fast-forward; Repos mit lokalen Änderungen überspringen. |
| Push | Aktiven lokalen Branch zum konfigurierten Upstream-Remote und -Branch übertragen. Kein Force-Push und keine automatische Veröffentlichung anderer Branches oder Tags. |
| Aktualisieren | Lokalen Status neu einlesen; keine Netzwerkabfrage. |

Aktionen betreffen **alle angehakten Repositories, auch ausgefilterte Zeilen**.
Die Anzahl ausgeblendeter ausgewählter Repositories wird angezeigt.

Remote-Branches und Commit-Zähler entsprechen dem **letzten Fetch**. Für aktuelle
Serverdaten zuerst Fetch ausführen. Zur Anmeldung werden die vorhandenen Git-
Zugangsdaten bzw. der SSH-Agent verwendet. Details und Tastenkürzel stehen im
[Benutzerhandbuch](docs/de/user-guide.md).

## Optionale Paketinstallation

Das ausgecheckte Projekt lässt sich in einer virtuellen Umgebung installieren:

```shell
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m git_repo_manager
```

Unter Linux/macOS stattdessen `.venv/bin/python` verwenden. Die Installation
stellt außerdem den Desktop-Befehl `git-repo-manager` im Skriptverzeichnis der
Umgebung bereit. Ein installiertes Paket beginnt beim ersten Start im aktuellen
Arbeitsverzeichnis.

Diese Anleitung beschreibt die Installation **aus diesem Quellcode** und setzt
keine Veröffentlichung auf PyPI voraus.

## Projektstruktur

```text
GitRepoManager/
├── src/git_repo_manager/    # Anwendungspaket
│   ├── gui.py              # Tkinter-Oberfläche und Hintergrundaufgaben
│   ├── git_backend.py      # Suche, Status und Git-Aktionen
│   ├── settings.py         # Benutzereinstellungen und Übernahme alter Daten
│   └── windows_job.py      # Abbruch von Windows-Unterprozessen
├── tests/                  # Backend-, GUI- und Einstellungstests
├── scripts/                # Teststarter und Dokumentationsprüfung
├── docs/
│   ├── en/                 # English guides
│   └── de/                 # Deutsche Anleitungen
├── .github/                # CI, Issue-Formulare und PR-Vorlage
├── app.py                  # Direkter Start aus dem Quellcode
├── start.bat / start.sh    # Startskripte
├── pyproject.toml          # Paketmetadaten und Build-Konfiguration
├── README.md / README.de.md
├── CONTRIBUTING.md / CONTRIBUTING.de.md
├── CHANGELOG.md
└── LICENSE
```

## Entwicklung und Prüfung

Die Tests verwenden temporäre lokale Repositories und Bare-Remotes. Sie verändern
keine bestehenden Projekte und kontaktieren keine externen Git-Server.

```shell
python scripts/test.py                  # Alle Tests; grafische Sitzung erforderlich
python scripts/test.py --backend-only   # Git und Einstellungen ohne Bildschirm
python scripts/test.py --gui-only       # Tkinter-Integration
python scripts/check_docs.py
```

Der GitHub-Workflow ist für Backend-Tests unter Windows und Linux mit Python 3.10
und 3.13, Windows-GUI-Tests und einen Paket-Build konfiguriert. Diese Konfiguration
bedeutet nicht, dass die entfernten CI-Aufträge bereits ausgeführt wurden.

Lokal wurde unter Windows mit Python 3.12 geprüft. Das Desktop-Verhalten unter
Linux/macOS wurde noch nicht manuell überprüft.

## Dokumentation und Beiträge

- [Dokumentationsübersicht](docs/README.md)
- [Benutzerhandbuch](docs/de/user-guide.md)
- [Entwicklung, Paketbau und Veröffentlichung](docs/de/development.md)
- [Architektur](docs/de/architecture.md)
- [Mitwirken](CONTRIBUTING.de.md) · [Änderungsprotokoll](CHANGELOG.md)

Fehlerberichte, Pull Requests und Verbesserungen an der Dokumentation sind auf
Deutsch und Englisch willkommen. Das Projekt steht unter der [MIT-Lizenz](LICENSE).
