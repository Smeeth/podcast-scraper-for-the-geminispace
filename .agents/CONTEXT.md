# Agent Context & Status

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

Dieses Dokument hält den aktuellen Projektstatus, offene Punkte und Kontextinformationen für nachfolgende Agenten-Sessions fest.

## Aktueller Entwicklungsstand (Abgeschlossen)

- [x] Initialisierung der Living Agent Documentation (`.agents/`)
- [x] Architektur-Definition (4-Schichten)
- [x] Lizenzierung unter GNU GPL v3.0 mit SPDX-Headern in allen Quellcodedateien
- [x] Implementierung der Backend-Kernkomponenten (FastAPI, SQLAlchemy 2.0 Async, Pydantic v2)
- [x] Implementierung der Scraper (YouTube via `yt-dlp`, RSS/Apple via `defusedxml` & iTunes Lookup)
- [x] Integration des Gemini AI Services (`google-genai` SDK mit Prompt-Templates für Wikipedia, Gäste, Q&A, Chat)
- [x] Erstellung der Bootstrap 5 Dark Mode Oberfläche (`app/static/`) lokal gebündelt ohne externe CDNs
- [x] Docker-Setup (`Dockerfile` mit Non-Root User `appuser`, Python 3.11-slim, ffmpeg) & `docker-compose.yaml` (PostgreSQL 16 Alpine)
- [x] Exporter & Webspace Publisher für Geminispace (`.gmi`) und Gopherspace (`gophermap`)
- [x] End-to-End Verifikation & automatisierte Test-Suite (`tests/test_core.py`, `tests/test_integration.py` – 28/28 Tests bestanden)
- [x] GitHub Ecosystem (`.github/` mit CI, Docker-Build, CodeQL, Dependabot, Issue/PR-Templates & Verifikationsskripten auf `ubuntu-latest`)
- [x] ADR-0003: Granulare Single-File Commit-Strategie in englischer Sprache
- [x] ADR-0004: Explizite, ungekürzte Dateiendungen (`.yaml` statt `.yml`)

## System-Merkmale & Sicherheitsrichtlinien

1. **Lokal gebündeltes Bootstrap 5:** Vollständig unter `app/static/vendor/` bereitgestellt, kompatibel mit strikter CSP (`default-src 'self'`).
2. **SSRF-Validierung:** Bei IP-Auflösung von Domains werden DNS-Antworten auf RFC-1918, Cloud-Metadaten (`169.254.169.254`) und Loopback-Ranges geprüft.
3. **Flexible Datenbankanbindung:** Standardmäßig über isolierten PostgreSQL 16 Container in `docker-compose.yaml`, nahtlos umschaltbar auf externe PostgreSQL-Instanzen über `DATABASE_URL`.
4. **Granulare Versionskontrolle (ADR-0003):** Jeder Dateizusatz und jede Dateiänderung wird in einem separaten Commit dokumentiert.
5. **Ungekürzte Dateiendungen (ADR-0004):** Ausschließlich `.yaml`, `.html`, `.md`, `.js`, `.json`.
