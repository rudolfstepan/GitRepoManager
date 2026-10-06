# Entwicklung, Paketbau und Veröffentlichung

[Dokumentation](../README.md) · [English](../en/development.md)

## Im Checkout arbeiten

Benötigt werden Python 3.10+ und Git. Die GUI benötigt außerdem Tkinter und eine
grafische Sitzung. Zur Laufzeit verwendet der Code nur die Python-Standardbibliothek.

```shell
python app.py
python app.py --version
python scripts/test.py
python scripts/check_docs.py
```

Quellcode-Starter und Testskript nehmen `src/` selbst in den Importpfad auf.
Ein installiertes Paket wird mit `python -m git_repo_manager` gestartet.
`src/git_repo_manager/gui.py` nicht direkt ausführen; seine Imports gehören zum Paket.

## Editierbare Entwicklungsumgebung

Eine virtuelle Umgebung erstellen und deren Interpreter ausdrücklich verwenden:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m git_repo_manager
```

Unter Linux/macOS `.venv\Scripts\python` durch `.venv/bin/python` ersetzen.
Das optionale Extra `dev` enthält Werkzeuge für Paketbau und Metadatenprüfung.
Anwendung und unittest-Prüfungen benötigen diese Werkzeuge nicht.

## Tests

```shell
python scripts/test.py
python scripts/test.py --backend-only
python scripts/test.py --gui-only
python scripts/check_docs.py
```

Backend- und Einstellungstests benötigen keinen Bildschirm. GUI-Tests verwenden
echte Tk-Widgets und eine grafische Sitzung; auf Linux-CI-Systemen können sie unter
Xvfb laufen. Das Testskript trennt Backend- und GUI-Prüfungen in eigene Interpreter.

Die Integrationstests erstellen temporäre Repositories, einen lokalen Bare-Remote
und Klone. Die Umgebung der Git-Unterprozesse isoliert globale/Systemkonfiguration
und verwendet eigene Test-Autordaten. Geprüft werden Suche, Branches, Push/Fetch/
Pull, Divergenz, Abbruch, Zeitlimits und Einstellungsübernahme. GUI-Tests prüfen
Auswahl, Filter, Branch-Details und gemeinsame Aktionen.

Die Tests kontaktieren keine externen Remotes. Persönliche Projekte dürfen die
temporären Test-Repositories nicht ersetzen.

Der GitHub-Workflow konfiguriert Windows-/Linux-Backend-Prüfungen mit Python 3.10
und 3.13, Windows-GUI-Prüfungen und einen Paket-Build. Er veröffentlicht keine Pakete.
Ergebnisse der entfernten CI gibt es nach dem Push zu einem GitHub-Repository.

## Pakete bauen

Mit installierten Entwicklungswerkzeugen im Projektordner ausführen:

```shell
python -m build
python -m twine check dist/*
```

In `dist/` entstehen Quellarchiv und Wheel. Das Wheel enthält nur Anwendungspaket
und Metadaten. Das Quellarchiv enthält zusätzlich beide READMEs, Anleitungen,
Tests, Startskripte und Beitragsrichtlinien. Lokale Einstellungen, Zugangsdaten,
virtuelle Umgebungen und Build-Caches sind ausgeschlossen.

Ist eine passende setuptools-Version bereits installiert, lässt sich ein Wheel
auch ohne Netzwerkzugriff bauen:

```shell
python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist .
```

Das Wheel in einer frischen Umgebung außerhalb des Quellcode-Importpfads prüfen:

```shell
python -m venv .verify/venv
# Windows; auf anderen Plattformen den Interpreterpfad ersetzen:
.verify\venv\Scripts\python -m pip install --no-deps dist/git_repo_manager-0.1.0-py3-none-any.whl
.verify\venv\Scripts\python -m git_repo_manager --version
```

Den Dateinamen an die aktuelle Version anpassen. Die Paketmetadaten folgen der
[Python-Packaging-Anleitung](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).

## Veröffentlichung vorbereiten

1. `__version__` in `src/git_repo_manager/__init__.py` aktualisieren. Die
   Paketmetadaten lesen diesen Wert; keine zweite Versionsquelle einführen.
2. Beide Dokumentationsverzeichnisse und das zweisprachige Änderungsprotokoll aktualisieren.
3. Tests, Dokumentationsprüfung und Paket-Build ausführen.
4. Wheel in einer frischen Umgebung installieren und den Desktop-Start prüfen.
5. Datum im Änderungsprotokoll ergänzen, geprüfte Dateien committen und Version taggen.
6. Sobald Remote und Veröffentlichungsziel feststehen, Tag und Artefakte gezielt veröffentlichen.

Das Projekt enthält keine Remote-URL, Veröffentlichungszugangsdaten oder
automatische Deployment-Konfiguration. Vor einer gehosteten Veröffentlichung die
tatsächlichen Repository-/Dokumentations-URLs in den Paketmetadaten ergänzen,
damit Links auf dem gewählten Paketindex korrekt aufgelöst werden.
