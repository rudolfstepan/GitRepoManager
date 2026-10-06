# Mitwirken

[English](CONTRIBUTING.md) · [Projekt-README](README.de.md)

Beiträge sind auf Deutsch und Englisch willkommen. Diskussionen sollen
respektvoll, konkret und auf die jeweilige Änderung bezogen bleiben.

## Ein Problem melden

Bei einem auf GitHub gehosteten Projekt die Fehlerbericht-Vorlage verwenden.
Anwendungsversion (`python app.py --version`), Python-/Git-Versionen,
Betriebssystem, Schritte zur Reproduktion sowie erwartetes und tatsächliches
Verhalten nennen. Git-Probleme möglichst mit Wegwerf-Repositories nachstellen.
Zugangsdaten und persönliche Repository-Pfade aus geteilten Protokollen entfernen.

Die Funktionswunsch-Vorlage beschreibt den Arbeitsablauf und das gewünschte Ergebnis.

## Eine Änderung umsetzen

1. Für die Änderung einen Branch im eigenen Checkout erstellen.
2. Anwendungscode unter `src/git_repo_manager/`, Tests unter `tests/` und
   unterstützende Entwicklungsbefehle unter `scripts/` ablegen.
3. Laufzeitabhängigkeiten auf die Standardbibliothek beschränken, sofern eine
   Funktion keinen klaren Grund für ein zusätzliches Paket liefert.
4. Passende Tests und `python scripts/check_docs.py` ausführen. Bei Backend- oder
   GUI-Änderungen zusätzlich `python scripts/test.py` in einer grafischen Sitzung ausführen.
5. Deutsche und englische Dokumentation gemeinsam aktualisieren und das Änderungsprotokoll ergänzen.
6. Verhaltensänderung, Prüfung und verbleibende Einschränkungen im PR erläutern.

Git-Aktionen ausdrücklich begrenzen. Pull per Fast-forward und Push für einen
Branch erhalten, sofern eine geprüfte Funktion ihr sichtbares Verhalten nicht
gezielt verändert. Tk-Aufrufe bleiben im Hauptthread. Tests verwenden temporäre
Repositories und lokale Remotes, ohne Netzwerkzugriff oder Änderungen an eigenen Projekten.

Keine Benutzereinstellungen, Zugangsdaten, Build-Artefakte oder virtuellen
Umgebungen committen. Die [Entwicklungsanleitung](docs/de/development.md)
beschreibt Einrichtung, Paketbau und Veröffentlichung.

## Lizenz

Eingereichte Beiträge werden unter der [MIT-Lizenz](LICENSE) dieses Projekts
bereitgestellt. Erforderliche Hinweise für übernommenen Drittcode bleiben erhalten.
