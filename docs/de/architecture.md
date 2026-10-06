# Architektur

[Dokumentation](../README.md) · [English](../en/architecture.md)

## Zuständigkeit der Module

| Modul | Aufgabe |
| --- | --- |
| `gui.py` | Tk-Widgets, Filter, Auswahl, Anzeige und Koordination der Hintergrundaufgaben. |
| `git_backend.py` | Repository-Suche, Git-Unterprozesse, Statusauswertung, Datenmodelle und Regeln für Aktionen. |
| `settings.py` | Benutzerpfade, Standardordner, validierte Einstellungen und Übernahme alter Daten. |
| `windows_job.py` | Windows-Jobobjekte zum Abbrechen von Git einschließlich Unterprozessen. |
| `__init__.py` | Paketkennung und zentrale Versionsnummer. |
| `__main__.py` | Startpunkt für das installierte Python-Modul. |
| `app.py` im Hauptordner | Schlanker Quellcode-Starter ohne doppelte Anwendungslogik. |

Laufzeitabhängigkeiten sind Python-Standardbibliothek, Tcl/Tk und das installierte
Git-Programm. Paketbau und optionale Entwicklungswerkzeuge sind davon getrennt.

## Suche und Status

Die Suche durchläuft Verzeichnisse iterativ. Sie erkennt `.git`-Ordner und -Dateien
sowie Merkmale von Bare-Repositories. Arbeitsverzeichnisse werden weiter durchsucht,
um verschachtelte Repos zu finden; Git-interne Ordner und Verzeichnislinks entfallen.

Während der Suche lesen bis zu vier Worker den Status. Ausgewertet wird die
NUL-getrennte Porcelain-v2-Ausgabe von Git, unabhängig von lokalisierten
Menschenlese-Ausgaben. Bei Umbenennungen wird auch der folgende Datensatz mit dem
ursprünglichen Pfad berücksichtigt. Branch-Daten stammen aus `for-each-ref`;
symbolische Remote-HEAD-Aliase werden ausgelassen.

Die Dataclasses `Repository`, `Branch` und `GitResult` transportieren Daten zur GUI.
Git-Pfade und Argumente werden als Liste ohne Shell übergeben.
Lesevorgänge deaktivieren optionale Git-Sperren.

## Oberfläche und Hintergrundaufgaben

Tk-Aufrufe bleiben im Hauptthread. Worker schreiben Repository-Zustände, Meldungen,
Ergebnisse und Abschlussereignisse in eine threadsichere Queue. Die Oberfläche
verarbeitet sie alle 80 Millisekunden. Checkboxen bleiben beim Neuaufbau der Liste erhalten.

Normalisierte Repository-Pfade dienen als Zeilenkennung. Gleichnamige Projekte
bleiben dadurch unterscheidbar. Die Suche ändert die Sichtbarkeit, nicht die Checkbox-Auswahl.

Gemeinsame Aktionen laufen nacheinander. Jedes Repository wird unmittelbar davor
neu gelesen; Ergebnisse werden einzeln festgehalten und der Status danach erneut
geladen. Fehler unterbrechen die weitere Auswahl nicht.

## Git-Regeln und Abbruch

Fetch betrifft alle Remotes und entfernt veraltete Remote-Tracking-Refs. Pull
benötigt ein sauberes Arbeitsverzeichnis und erlaubt nur Fast-forward, ohne Rebase
oder automatischen Stash. Push übergibt Remote und Ref-Spezifikation ausdrücklich
und überschreibt Mirror-/Tag-Following-Verhalten für diesen Aufruf.

Ein Abbruchsignal wird zwischen Repositories und während der Git-Kommunikation
geprüft. Windows-Jobobjekte erfassen Unterprozesse; taskkill dient als Rückfallweg.
Auf anderen Systemen startet Git in einer eigenen Prozessgruppe. Zeitlimits
verwenden denselben Abbruchweg. Bereits abgeschlossene Aktionen werden nicht zurückgesetzt.

Git-Eigentümerprüfungen bleiben aktiv. Die Anmeldung nutzt die vorhandene
Git-/SSH-Umgebung; Terminal- und interaktive Git-Credential-Manager-Abfragen sind deaktiviert.

## Einstellungen und Paketstruktur

Der Quellcode liegt unter `src/git_repo_manager/`. Das Wheel installiert dieses
Paket samt Startpunkt, ohne Hauptordner-Starter, Tests oder Benutzerdaten.
Das Quellarchiv enthält zusätzlich Skripte und zweisprachige Dokumentation.

Einstellungen liegen im Benutzerprofil, nie in site-packages. Fehlt die neue
Datei, liest ein Checkout die bisherige portable Datei. Nur bekannte Felder mit
passenden Datentypen werden übernommen. Speichern erstellt bei Bedarf den
Konfigurationsordner und ersetzt die Datei über eine temporäre Datei im selben Ordner.

Die Testumgebung steuert die Git-Unterprozesse, ohne die native Tcl-Prozessumgebung
zu verändern. Sämtliche Test-Repositories und -Remotes sind temporär.
