# 📻 Podcast & Media Channel Researcher & AI Analyzer

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![UI: Bootstrap 5 Dark Mode](https://img.shields.io/badge/UI-Bootstrap%205%20Dark-7952B3.svg?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Security: ADR-0001](https://img.shields.io/badge/Security-Security%20%3E%20Performance-red.svg)](#-sicherheitsarchitektur-adr-0001)

Eine vollständige, modulare und sicherheitsgehärtete Web-Applikation zur automatisierten Erfassung, Analyse, Archivierung und Wikipedia-Wikitext-Generierung von Podcasts, YouTube-Kanälen und RSS-Medienfeeds unter der **GNU General Public License v3 (GPL-3.0)**.

---

## 🌟 Highlights & Funktionen

- **🎙️ Multi-Plattform Scraper:**
  - **YouTube:** Kanäle (`@Kanal`), Playlists und Einzelvideos via Python `yt-dlp` API & `youtube-transcript-api`.
  - **RSS 2.0 & Atom:** Universelle Feed-Unterstützung inkl. iTunes/Podcast-Namespaces (`<podcast:transcript>`, Kapitelmarken, Show Notes).
  - **Apple Podcasts:** Automatische Feed-Auflösung via iTunes Lookup API.
- **🛡️ Maximale Sicherheit (ADR-0001):**
  - Strikte SSRF-Validierung (Blockierung von Cloud-Metadata-IPs, Private IPs, Loopback).
  - Gehärtetes XML-Parsing mit `defusedxml` (Schutz vor XXE & XML-Bomben).
  - Keine Shell-Ausführungen / Command Injection Schutz.
  - Strikte Content Security Policy (CSP) & isoliertes Non-Root-Image (`appuser`).
- **🤖 Gemini AI Recherche-Labor (`google-genai` SDK):**
  - **📊 Wikipedia-Wikitext-Generator:** Ein-Klick-Erstellung standardkonformer MediaWiki-Episodentabellen (`{| class="wikitable sortable" ... |}`).
  - **👥 Gäste- & Themen-Extraktor:** Strukturierte Profile aller Gäste, Rollen und thematischen Schwerpunkte.
  - **🔍 Semantisches Q&A:** Präzise, faktenbasierte Antworten gestützt auf Show Notes und Transkripte.
  - **💬 Freier Recherche-Assistent:** Flexibler Dialog für vergleichende Analysen.
- **💾 Export-Center:** Ein-Klick-Download aller Daten in **JSON**, **CSV**, **Markdown** und **Wikitext**.
- **🎨 Modernes Bootstrap 5 Dark Mode Interface:**
  - Lokal gebündelt (keine anfälligen externen CDNs).
  - Reaktive Archiv-Sidebar, filterbare Episodentabelle und Offcanvas-Drawer für Show Notes & Transkripte.

---

## 🏛️ 4-Schichten-Architektur

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Schicht 1: Gehärtete Weboberfläche (Bootstrap 5 Dark Mode + Vanilla JS) │
├─────────────────────────────────────────────────────────────────────────┤
│ Schicht 2: Recherche-Archiv & Volltext-Explorer                         │
├─────────────────────────────────────────────────────────────────────────┤
│ Schicht 3: Modulare Scraper- & Analytik-Engine (FastAPI + Gemini SDK)  │
│   ├── YouTubeScraper (yt-dlp Python-API, Transcript-API)                │
│   ├── RSSScraper (defusedxml, feedparser, Apple Podcasts Resolver)      │
│   └── GeminiAIService (Chunking & spezialisierte Prompt-Templates)      │
├─────────────────────────────────────────────────────────────────────────┤
│ Schicht 4: Datenbank-Persistenz (PostgreSQL 16 / SQLAlchemy 2.0 Async)  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart mit Docker Compose

Der schnellste Weg zum Starten der vollständigen Anwendung inkl. isolierter PostgreSQL-Datenbank:

```bash
# 1. Repository klonen und in das Verzeichnis wechseln
cd "podcast scraper for the geminispace"

# 2. Konfiguration anpassen (optional: GEMINI_API_KEY hinterlegen)
cp .env.example .env

# 3. Stack bauen und starten
docker compose up --build
```

Die Anwendung ist sofort unter **[http://localhost:8000](http://localhost:8000)** erreichbar.

---

## 🛠️ Lokale Entwicklung ohne Docker

Für Entwickler, die Python direkt lokal ausführen möchten:

```bash
# 1. Virtuelle Umgebung erstellen und aktivieren
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Umgebungsvariablen setzen (.env)
# Für SQLite Fallback (lokale Entwicklung ohne Postgres):
# DATABASE_URL=sqlite+aiosqlite:///./podcast_researcher.db

# 4. Server starten
uvicorn app.main:app --reload --port 8000
```

---

## 🔌 Anbindung an eine externe PostgreSQL-Instanz

Das System ist vollständig entkoppelt. Um eine externe Datenbank (z.B. AWS RDS, DigitalOcean Managed Database, lokales PostgreSQL) zu nutzen, passe einfach `DATABASE_URL` in der `.env` an:

```env
DATABASE_URL=postgresql+asyncpg://mein_user:mein_passwort@db.meinedomain.de:5432/meine_db
```

Falls du Docker Compose verwendest und nur den `app`-Service gegen eine externe Datenbank starten möchtest:

```bash
docker compose run -p 8000:8000 -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" app
```

---

## 🔑 Google Gemini AI Konfiguration

Trage deinen API-Schlüssel in die `.env` Datei ein:

```env
GEMINI_API_KEY=AIzaSy...DeinSchluessel
GEMINI_MODEL=gemini-2.5-flash
```

> **Hinweis:** Falls kein Key hinterlegt ist, funktioniert der Scraper, das Archiv, die Filterung und der Export weiterhin uneingeschränkt im Offline-Modus.

---

## 🛡️ Sicherheitsarchitektur (ADR-0001)

Jede Komponente folgt dem Leitprinzip **`Security > Performance > Usability`**:

1. **SSRF-Schutz:** URL-Eingaben werden gegen RFC-1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), Loopback, IPv6-Local und Cloud-Metadaten-IPs (`169.254.169.254`) validiert.
2. **defusedxml:** Alle XML/RSS/Atom-Daten werden vor der Verarbeitung gegen XML External Entity Attacks (XXE) und Entitäten-Expansion abgesichert.
3. **Keine Shell-Aufrufe:** `yt-dlp` wird strikt über die Python-interne API instanziiert.
4. **Secrets-Schutz:** API-Keys werden in Logs maskiert und niemals an den Client gesendet.
5. **Container-Härtung:** Docker-Container läuft als unprivilegierter Benutzer `appuser` (UID 10001).
6. **CSP & Local Assets:** Bootstrap 5 ist lokal eingebunden; keine externen Skript-Abhängigkeiten.

---

## 📚 Living Agent Documentation

Das Verzeichnis [`.agents/`](.agents/) enthält die kontinuierlich gepflegte Architektur- und Entscheidungsdokumentation:
- [`.agents/ARCHITECTURE.md`](.agents/ARCHITECTURE.md): Modulübersicht und Datenfluss.
- [`.agents/DECISIONS/ADR-0001-security-first.md`](.agents/DECISIONS/ADR-0001-security-first.md): Grundsatzentscheidung Sicherheit.
- [`.agents/DECISIONS/ADR-0002-modular-scraper-adapter.md`](.agents/DECISIONS/ADR-0002-modular-scraper-adapter.md): Plugin- und Adapter-Muster.
- [`.agents/CONTEXT.md`](.agents/CONTEXT.md): Status & Roadmap.

---

## 📄 Lizenz

Dieses Projekt ist unter der **GNU General Public License v3.0 (GPL-3.0)** lizenziert. Siehe die Datei [LICENSE](LICENSE) für den vollständigen Lizenztext.

```text
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```
