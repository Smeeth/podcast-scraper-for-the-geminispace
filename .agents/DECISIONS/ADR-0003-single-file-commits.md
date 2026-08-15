# ADR-0003: Granulare Einzeldatei-Commits (Single-File Commits)

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

## Status
Akzeptiert

## Kontext
In einem kollaborativen und agentengesteuerten Open-Source-Projekt (GPL-3.0) ist eine saubere, transparente und feingranulare Versionsgeschichte von zentraler Bedeutung. Große Sammel-Commits erschweren Code-Reviews, machen `git bisect` und selektive Reverts unübersichtlich und verschleiern den Zweck einzelner Dateiänderungen.

## Entscheidung
Für die Versionsverwaltung im Repository gilt das Prinzip **Single-File Commits**:

1. **Ein Commit pro Datei:**
   - Jede neue Datei wird in einem eigenen, separaten Git-Commit hinzugefügt.
   - Jede modifizierte Datei wird in einem separaten Git-Commit aktualisiert.

2. **Commit-Nachrichten in englischer Sprache:**
   - Sämtliche Commit-Messages werden auf Englisch verfasst.
   - Es wird der Conventional Commits Standard verwendet (z. B. `feat(...)`, `fix(...)`, `docs(...)`, `chore(...)`, `ci(...)`, `test(...)`).

3. **Präzise Beschreibung:**
   - Die Commit-Message muss den genauen Zweck und die Verantwortung der betroffenen Datei widerspiegeln.

## Konsequenzen
- **Vorteile:**
  - Maximale Nachvollziehbarkeit für Entwickler und KI-Agenten.
  - Einfache, konfliktfreie Reverts einzelner Module oder Konfigurationen.
  - Höchste Transparenz bei Sicherheits-Audits und Code-Reviews.
- **Trade-offs:**
  - Größere Gesamtzahl an Commits in der Git-Historie.
