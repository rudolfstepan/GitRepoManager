# Benutzerhandbuch

[Dokumentation](../README.md) · [English](../en/user-guide.md)

## Start und Suchordner

Benötigt werden Python 3.10+, Tkinter und Git im PATH. Der Windows-Python-Installer
bietet Tcl/Tk an; unter Linux kann es ein separates Systempaket sein.
Für den Start aus dem Quellcode sind keine pip-Pakete erforderlich.

Mit `python app.py`, unter Windows per Doppelklick auf `start.bat` oder unter
Linux/macOS mit `sh start.sh` starten. Eine ausdrückliche Angabe wie
`python app.py "Pfad/zu/Projekten"` hat Vorrang vor dem gespeicherten Ordner.
Sonst wird der letzte Ordner verwendet, danach der übergeordnete Projektordner
bzw. bei einem installierten Paket das aktuelle Arbeitsverzeichnis.

## Repositories finden und auswählen

1. **Suchordner** setzen oder **Ordner wählen** verwenden.
2. Mit **Repos suchen** den Suchordner und seine direkten Unterordner prüfen.
   **Rekursive Suche** aktivieren, um auch tiefere Unterordner zu durchsuchen.
   Die Checkbox ist standardmäßig ausgeschaltet; die Einstellung wird gespeichert.
3. Ein Projekt links anklicken. Rechts erscheinen Status, lokale Änderungen und
   die Projektaktionen **Fetch · Abrufen**, **Pull · Übernehmen**, **Push · Senden**.
   Dafür sind keine Häkchen nötig.
4. Für Sammelaktionen Repositories in der ersten Spalte anhaken. **Sichtbare auswählen**
   markiert alle sichtbaren Zeilen; die Checkbox im Spaltenkopf schaltet diese um.
5. **Auswahl aufheben** entfernt alle Häkchen.

Die markierte Zeile bestimmt die Projektaktionen und Details rechts. Checkboxen
bestimmen ausschließlich die Sammelaktionen unten und werden gespeichert.

Die Sammelaktionen stehen unten: **Fetch für angehakte**, **Pull für angehakte**
und **Push für angehakte**. Direkt darüber
steht, wie viele angehakte Projekte betroffen sind, einschließlich ausgeblendeter
Projekte. **Status neu laden · F5** liest den lokalen Status aller Projekte neu.

Der Reiter **Projekt & Branches** zeigt Pfad, Remotes und Branches der markierten
Zeile. Im Reiter **Protokoll** stehen die ausführlichen Ergebnisse.
**Filter löschen** setzt Suchtext, **Nur Änderungen** und **Nur Auswahl** zurück.

Pull wird bei lokalen Änderungen (auch neuen, unversionierten Dateien) als
**Übersprungen** angezeigt. Der Grund und der nächste Schritt stehen in
**Projekt & Branches**. Die übrigen angehakten Projekte werden weiterverarbeitet.
Die Zusammenfassung zählt erfolgreiche, übersprungene und fehlgeschlagene Aktionen
getrennt. Lokale Änderungen werden nicht automatisch gestasht oder verworfen.

Die Suche berücksichtigt Projektnamen, Pfade, Remotes und bekannte Branch-Namen.
Alle durch Leerzeichen getrennten Suchbegriffe müssen passen.
Spaltenüberschriften sortieren die Liste. **Nur Auswahl** zeigt angehakte Repos.
**Nur Änderungen** berücksichtigt lokale Änderungen, vorausliegende/nachzuholende
Commits und Lesefehler.

Filter entfernen keine Häkchen. Sammelaktionen betreffen **alle angehakten Repositories,
auch ausgefilterte Zeilen**. Der Zähler zeigt ausgeblendete ausgewählte Repos an.

Die Suche findet verschachtelte Repositories, Submodule mit einer `.git`-Datei,
verknüpfte Worktrees und Bare-Repositories. Verzeichnislinks und Git-interne Ordner
werden übersprungen. Der optionale Abhängigkeitsfilter schließt `node_modules`,
`.venv`, `venv`, `__pycache__`, `.tox` und `.mypy_cache` aus. Er ist
standardmäßig ausgeschaltet.

## Nicht committete Änderungen ansehen

Ein Projekt in der Liste markieren und den Reiter **Lokale Änderungen** öffnen.
Die Dateiliste unterscheidet **Vorgemerkt** (im Index für den nächsten Commit),
**Nicht vorgemerkt**, **Neu** und **Konflikt**. Eine Datei kann in zwei Bereichen
erscheinen, wenn sie nach dem Vormerken nochmals bearbeitet wurde.

Die erste Datei wird automatisch angezeigt. Eine andere Datei anklicken, um
darunter deren Diff zu sehen: **Grün / +** bedeutet
hinzugefügt, **Rot / −** bedeutet entfernt. Neue Dateien zeigen ihren aktuellen
Textinhalt. Binärdateien erhalten einen Hinweis statt einer Textvorschau.
Große Vorschauen werden mit einem sichtbaren Hinweis gekürzt.

**Änderungen neu laden** aktualisiert die Ansicht nach Änderungen im Editor.
Die Ansicht liest ausschließlich; sie verändert weder Dateien noch den Index.
Das Farbschema nutzt Petrol für die Auswahl, dunklen Text auf hellen Flächen
und zusätzliche Statusbezeichnungen, damit Farben nicht die einzige Orientierung sind.

## Branches und Status

Die Liste links zeigt Projekt und Status. Der Kopfbereich rechts zeigt den
aktiven Branch sowie **↑** zu sendende und **↓** zu holende Commits.
Remotes und Ergebnisse stehen im Reiter **Projekt & Branches**.

Der Reiter **Projekt & Branches** zeigt lokale und Remote-Tracking-Branches.
Ein Stern markiert den aktiven Branch. Upstreams und Abweichungen sind ebenfalls
sichtbar. Wechsel, Erstellung und Löschung von Branches erfolgen über Git im Terminal.

Remote-Branches und Zähler entsprechen dem **letzten Fetch**. Für aktuelle
Serverdaten zuerst Fetch ausführen. Suche und lokale Aktualisierung kontaktieren
keinen Server.

## Gemeinsame Aktionen

Repositories werden nacheinander verarbeitet. Vor jeder Aktion wird der Status
neu gelesen. Ein Fehler verhindert die Verarbeitung der restlichen Auswahl nicht.
Die Oberfläche bleibt bedienbar; Checkboxen sind während einer Aktion gesperrt.

| Schaltfläche | Verhalten |
| --- | --- |
| **Fetch** | `git fetch --all --prune`: alle Remotes abrufen und veraltete Remote-Tracking-Refs entfernen. |
| **Pull (ff-only)** | `git pull --ff-only --no-rebase --no-autostash`: aktiven Branch aktualisieren; lokale Änderungen führen zum Überspringen. |
| **Push** | Ausdrückliche Ref-Spezifikation vom lokalen Branch zum Upstream; Force, Mirror, automatisches Mitübertragen von Tags und rekursives Submodul-Push sind für den Aufruf ausgeschaltet. |
| **Status aktualisieren** | Alle gefundenen Repositories lokal neu einlesen. |
| **Repos suchen** | Erneut suchen, um neue oder verschobene Repositories zu finden. |

Push verwendet den konfigurierten Upstream-Remote und -Branch, kein abweichendes
`pushRemote`, `remote.pushDefault` oder Matching-Refspec. Einen Remote-Upstream
zuvor im gewohnten Git-Ablauf einrichten; die Anwendung erstellt ihn nicht.

Pull und Push benötigen einen lokalen Branch mit Commit und Remote-Upstream.
Bei Bare-Repositories steht nur Fetch zur Verfügung. Die Anwendung erstellt
keine Commits oder Stashes.

**Abbrechen** stoppt die Verarbeitung und verhindert weitere vorgemerkte Aktionen.
Abgeschlossene oder übertragene Änderungen bleiben bestehen; Abbruch bedeutet
kein Zurücksetzen. Netzwerkaktionen haben ein Zeitlimit von fünf Minuten je
Repository, lokale Git-Lesebefehle jeweils 45 Sekunden.

## Ergebnisse, Navigation und Tastenkürzel

**Letzte Aktion** zeigt das jüngste Ergebnis je Repository.
**Aktivität & Ergebnisse** enthält Befehle, Ausgaben und Zusammenfassungen.
**Speichern** exportiert das Protokoll; die Anzeige hält etwa 12.000 Zeilen vor.

**Ordner öffnen**, **Terminal öffnen** und **Pfad kopieren** beziehen sich auf die
markierte Zeile. Das Kontextmenü bietet dieselben Funktionen. Ein Doppelklick
auf einen Projektnamen öffnet den Ordner.

| Tastenkürzel | Funktion |
| --- | --- |
| F5 | Lokalen Status aktualisieren |
| Strg+F | Suchfeld fokussieren |
| Leertaste | Checkbox der markierten Zeile umschalten, wenn die Liste den Fokus hat |
| Strg+A | Alle sichtbaren Repos anhaken, wenn die Liste den Fokus hat |
| Escape | Laufende Verarbeitung abbrechen |

## Einstellungen

Suchordner, Fenstergröße und -position, Checkbox-Auswahl sowie Abhängigkeitsfilter
werden im Benutzerprofil gespeichert.

| Plattform | Datei |
| --- | --- |
| Windows | `%APPDATA%\GitRepoManager\state.json` |
| macOS | `~/Library/Application Support/GitRepoManager/state.json` |
| Linux | `$XDG_CONFIG_HOME/git-repo-manager/state.json` oder `~/.config/git-repo-manager/state.json` |

Existiert keine neue Datei, liest ein Checkout die bisherige
`.git-repo-manager.json` im Projektordner. Speichern schreibt die neue Datei und
belässt das Original unverändert. Einstellungen sind von Git und Paketdateien ausgeschlossen.

## Fehlerbehebung

| Problem | Prüfen bzw. beheben |
| --- | --- |
| Git fehlt | Git installieren und die Anwendung wegen des geänderten PATH neu starten. |
| Tkinter- oder `init.tcl`-Fehler | `python -m tkinter` mit demselben Interpreter prüfen; bei Bedarf dessen Tcl/Tk-Komponente reparieren. |
| Anmeldung scheitert | Git im normalen Terminal anmelden oder den SSH-Agent einrichten, dann wiederholen. |
| Upstream fehlt | Tracking-Branch im gewohnten Git-Ablauf einrichten. |
| Pull übersprungen | Änderungen selbst committen oder stashen. |
| Pull abgelehnt | Auseinanderentwickelte Branches zunächst in Git auflösen. |
| Abweichende Eigentümerschaft | Eigentümer und Git-Meldung prüfen; Eigentümerprüfungen bleiben aktiv. |
| Suche langsam | Suchordner einschränken oder Abhängigkeitsordner überspringen. |

Git-Terminalabfragen und interaktive Git-Credential-Manager-Abfragen sind bei
Sammelaktionen deaktiviert. Bestehende Git-/SSH-Konfigurationen und Zugangsdaten
werden verwendet. Hooks und Git-Hilfsprogramme behalten ihr normales Verhalten;
die Anwendung isoliert keine unvertrauenswürdigen Repositories.
