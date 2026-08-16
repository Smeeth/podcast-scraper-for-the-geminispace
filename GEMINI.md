<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Antigravity & Agent Instructions: Podcast & Media Channel Researcher

Willkommen im Repository des **Podcast & Media Channel Researcher**. Diese Datei definiert die Kernrichtlinien, Architektur-Vorgaben und Sicherheitsstandards für Antigravity- und AI-Agenten in diesem Projekt.

---

## 1. Projektübersicht & Tech-Stack

Das Projekt ist ein asynchrones Python-Backend zur Recherche, Zusammenfassung und Veröffentlichung von Podcast- und Video-Inhalten (YouTube, RSS-Feeds, Apple Podcasts) mit Google Gemini KI-Integration und dualem Export in den **Geminispace** (`.gmi`) und **Gopherspace** (`gophermap`).

- **Sprache & Runtime**: Python 3.11+ (Asynchron mit `asyncio`)
- **Web-Framework**: FastAPI mit Uvicorn
- **Datenbank**: SQLAlchemy 2.0 (Async Engine mit PostgreSQL / `asyncpg` oder SQLite / `aiosqlite`)
- **Validierung & Config**: Pydantic v2 und `pydantic-settings`
- **Scraper & Parser**: `yt-dlp` (YouTube & Video/Audio), `defusedxml` & `feedparser` (RSS/Atom/Podcast-Feeds), `youtube-transcript-api`
- **KI-Service**: `google-genai` SDK (Google Gemini 2.5 Flash / Pro)
- **Frontend**: Bootstrap 5 Dark Mode (lokal gebündelt unter `app/static/vendor/`, ohne externe CDNs)
- **Containerisierung**: Docker (`python:3.11-slim`, Non-Root User `appuser`) & Docker Compose

---

## 2. Unabdingbare Sicherheits- & Architektur-Regeln (ADR-0001 & ADR-0002)

1. **Zero Secrets in Version Control (ADR-0001)**:
   - Niemals API-Keys, Passwörter, Token oder echte Zugangsdaten in Quellcodedateien oder Commits einbetten.
   - Alle Konfigurationen müssen über Umgebungsvariablen (`.env` basierend auf `.env.example`) via Pydantic `Settings` geladen werden.

2. **SSRF-Schutz (Server-Side Request Forgery)**:
   - Jede externe URL **muss** vor dem Abruf durch `app.config.is_safe_external_url(url)` validiert werden.
   - Private IP-Bereiche (RFC 1918), Loopback (`127.0.0.1`), Link-Local (`169.254.169.254`) und verbotene Protokolle (`file://`, `ftp://`, etc.) sind strikt geblockt.

3. **Sicheres XML- & Feed-Parsing**:
   - Für das Parsen von XML-Feeds ist **ausschließlich** `defusedxml` zu verwenden, um XML Entity Expansion (Billion Laughs) und XXE-Angriffe zu verhindern.

4. **Keine externen CDNs & strikte CSP**:
   - Alle JavaScript- und CSS-Bibliotheken müssen lokal unter `app/static/vendor/` liegen. Keine `<script src="https://cdn...">` Tags einfügen.

5. **Modulare Scraper-Architektur (ADR-0002)**:
   - Neue Medienquellen als Adapter via `BaseScraper` implementieren und in `app/scrapers/factory.py` registrieren.

---

## 3. Lizenzierung & SPDX-Pflicht

- Das gesamte Repository steht unter der **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.
- **Jede** neu erstellte Quellcodedatei (`.py`, `.js`, `.sh`, `.editorconfig`, `.ruff.toml`, etc.) muss den folgenden SPDX-Header in den ersten Zeilen tragen:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```

- In Markdown-Dateien:
```markdown
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->
```

---

## 4. Git Commit-Strategie (ADR-0003)

- **Granulare Single-File Commits**: Jede Dateiänderung bzw. Neuerstellung wird in einem separaten Commit committet.
- **Sprache**: Commit-Messages werden stets in **englischer Sprache** verfasst.
- **Format**: Conventional Commits (z.B. `feat(scraper): add apple podcast transcript support`, `fix(security): sanitize rss enclosure url`, `test(core): add ssrf test cases`).

---

## 5. Ungekürzte Dateiendungen (ADR-0004)

- **Standardkonforme Endungen**: Es sind stets vollwertige, ungekürzte Dateiendungen zu verwenden.
- **YAML**: Ausschließlich `.yaml` (z.B. `docker-compose.yaml`, `.github/workflows/*.yaml`, `.github/dependabot.yaml`). Die veraltete Form `.yml` ist unzulässig.
- **HTML & Dokumente**: Standardmäßig `.html`, `.md`, `.js`, `.json`.

---

## 6. Qualitätsprüfung & Verifikationsbefehle

Vor dem Abschluss einer Aufgabe sind folgende Verifikationsschritte auszuführen:

1. **SPDX-Header prüfen**:
   ```bash
   python .github/scripts/verify_spdx_headers.py
   ```
2. **Sicherheits-Audit ausführen**:
   ```bash
   python .github/scripts/security_audit.py
   ```
3. **Automatisierte Tests ausführen**:
   ```bash
   pytest tests -v
   ```
4. **Gemtext-Validierung**:
   ```bash
   python .github/scripts/gemtext_validator.py
   ```
5. **Code-Qualität & Linting**:
   ```bash
   ruff check app tests .github/scripts
   ```
