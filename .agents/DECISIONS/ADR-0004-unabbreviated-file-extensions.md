<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# ADR-0004: Explizite, ungekürzte Dateiendungen (Explicit & Unabbreviated File Extensions)

## Status
Akzeptiert

## Kontext
Historisch bedingt (z. B. 8.3-Dateinamensgrenzen unter MS-DOS) wurden viele Dateiendungen auf drei Zeichen abgekürzt (z. B. `.yml` statt `.yaml`, `.htm` statt `.html`). In modernen Entwicklungs- und Produktivumgebungen führt die Vermischung von verkürzten und vollständigen Endungen zu Inkonsistenzen in Tooling, Linting, Skripten und CI-Pipelines.
Im Projekt legen wir großen Wert auf Klarheit, Standardkonformität und die Vermeidung unvollständiger oder unnötig verkürzter Endungen.

## Entscheidung
Im gesamten Repository gilt für alle neu erstellten sowie bestehenden Dateien die verbindliche Vorgabe: **Es sind stets die ungekürzten, standardisierten Dateiendungen zu verwenden.**

Konkret gilt:
1. **YAML-Dateien:**
   - Ausschließliche Verwendung von `.yaml` (z. B. `.github/workflows/*.yaml`, `docker-compose.yaml`, `.github/dependabot.yaml`, `.github/ISSUE_TEMPLATE/*.yaml`).
   - Die veraltete/abgekürzte Form `.yml` ist im gesamten Repository unzulässig.
2. **Web- und Dokumentationsdateien:**
   - HTML-Dateien nutzen stets `.html` (kein `.htm`).
   - Markdown-Dateien nutzen `.md` standardkonform.
   - JavaScript- und JSON-Dateien nutzen `.js` und `.json`.
3. **Agenten & Automatisierung:**
   - KI-Agenten, Generatoren und Entwickler müssen neue Konfigurations- oder Quellcodedateien immer mit der vollen Endung anlegen.
   - Vorlagen aus externen Quellen, die `.yml` mitbringen, müssen beim Import zwingend auf `.yaml` angepasst werden.

## Konsequenzen
- **Vorteile:**
  - 100% einheitliche Dateistruktur im Projekt.
  - Verhindert Mehrdeutigkeiten und Mischformen im Repository.
  - Offizielle IANA/MIME- und Standard-Konformität (die offizielle YAML-Spezifikation empfiehlt `.yaml`).
- **Trade-offs:**
  - Bei externen Vorlagen oder Snippets muss aktiv auf die korrekte Endung geachtet und ggf. von `.yml` auf `.yaml` korrigiert werden.
