<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# 📻 Podcast & Media Channel Researcher & AI Analyzer

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash%20%2F%20Pro-8E75B2.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Spaces: Gemini & Gopher](https://img.shields.io/badge/Syndication-Geminispace%20%26%20Gopherspace-00bcd4.svg)](.agents/skills/export-spaces/SKILL.md)
[![Security: ADR-0001](https://img.shields.io/badge/Security-Security%20%3E%20Performance-red.svg)](.agents/DECISIONS/ADR-0001-security-first.md)

Eine modulare, asynchrone und sicherheitsgehärtete Plattform zur **automatisierten Recherche, Transkript-Analyse, Wikipedia-Synthese** und **retro-futuristischen Veröffentlichung** von Medienkanälen (YouTube, RSS-Feeds, Apple Podcasts) im **Geminispace** (`.gmi`) und **Gopherspace** (`gophermap`).

---

## 🎯 Das Konzept & der Workflow

Das Projekt löst das Problem, dass Podcasts und YouTube-Kanäle reich an Wissen sind, dieses Wissen jedoch oft schwer durchsuchbar, unstrukturiert und flüchtig ist. Der **Podcast & Media Channel Researcher** überführt Medieninhalte in strukturierte Wissensdatenbanken und bereitet sie für freie Wissensplattformen (Wikipedia, Geminispace) auf.

```text
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               DER NUTZER-WORKFLOW                                 │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 1. URL EINGEBEN        ▶ YouTube (@Kanal, Playlist), RSS-Feed oder Apple Podcast  │
│ 2. VORAB-CHECK (<1s)   ▶ Schneller Kanal-Check via /api/probe (Titel, Cover, Qty) │
│ 3. KONFIGURATION       ▶ Nutzer wählt Scrape-Tiefe (25 / 50 / 100 / Alle) & Audio │
│ 4. TIEFES METADATA-MINING ▶ Null Audio/Video Download: Metadaten, Kapitel & Text  │
│ 5. GEMINI AI SYNTHESE  ▶ Strukturierung in Wikipedia-Tabellen & Episodenlisten    │
│ 6. TRANSKRIPT-SUCHE    ▶ Volltextsuche mit YouTube-Zeitstempel-Direktsprungmarken │
│ 7. MULTI-CHANNEL EXPORT▶ Download (JSON/CSV/MD/Wiki) & Gemini/Gopher Publishing   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 2-Stufen-Erfassung (Vorab-Check ➔ Tiefenscan)

- **Stufe 1 (Probe):** Bei Eingabe einer URL prüft das Backend in Sekundenbruchteilen (`< 1s`), ob der Kanal existiert, und zeigt ein Info-Kärtchen mit Cover, Kanalbetreiber und geschätzter Episodenanzahl.
- **Stufe 2 (Konfigurierbarer Tiefenscan):** Der Nutzer entscheidet selbst über die Import-Tiefe (z. B. 25, 50, 100 oder alle Episoden) und ob Volltext-Transkripte mit Zeitstempeln geladen werden sollen.

### 2. Zero-Media-Storage-Prinzip (Reine Wissens- & Textdatenbank)

- Es werden **weder Gigabytes an Videodateien noch MP3s** auf dem Server oder Datenträger gespeichert.
- Das System extrahiert und persistiert ausschließlich strukturierte Metadaten: Show Notes, Episodennummern, Veröffentlichungsdaten, Kapitelmarken, Transkriptsegmente und direkte Quellverlinkungen (`audio_or_video_url`).

### 3. Wikipedia- & Episodenlisten-Synthese

- **MediaWiki Wikitable (`{| class="wikitable sortable" ... |}`):** Standardtabelle mit Titel, Datum, Dauer und Kurzzusammenfassungen.
- **Offizielle Wikipedia-Vorlage (`{{Episodenliste}}` / `{{Episodentabelle}}`):** Standardkonforme Vorlagenstruktur der deutschsprachigen Wikipedia.
- **Automatisches Wiki-Linking:** Google Gemini identifiziert automatisch relevante Personen, Interviewpartner und Fachbegriffe und setzt Wikipedia-Wikilinks (`[[Name]]`).
- **Delta-Modus:** Ermöglicht die isolierte Aufbereitung nur der neuesten Folgen zur einfachen manuellen Aktualisierung bestehender Wikipedia-Artikel.

### 4. Transkript-Recherche & YouTube-Deep-Links

- Sekundengenaue Volltextsuche über alle archivierten Folgen.
- Treffer werden mit Textauszug und klickbaren Zeitstempel-Chips (`▶️ [04:23]`) dargestellt, die direkt zur entsprechenden Sekunde auf YouTube springen (`&t=263s`).

### 5. Geminispace & Gopherspace Syndikation

- **Geminispace (`.gmi`):** Generiert Kapsel-Seiten und einen abonnierbaren Feed (`feed.gmi`) für Gemini-Browser (Lagrange, Elaho, Kristall).
- **Gopherspace (`gophermap`):** RFC-1436-konforme Menübäume für klassische Gopher-Clients.
- **Webspace Publisher:** Automatische Synchronisation aller archivierten Kanäle nach `public/gemini/` und `public/gopher/`.

---

## 🌟 Funktionsübersicht

| Funktionsbereich | Unterstützte Features & Technologien |

| :--- | :--- |
| **🎙️ Scraper-Adapter** | YouTube (`yt-dlp` Python-API), RSS 2.0 / Atom (`defusedxml`, `feedparser`), Apple Podcasts (iTunes Lookup) |
| **🤖 Gemini KI** | `google-genai` SDK (Gemini 2.5 Flash / Pro) für Zusammenfassungen, Gäste-Profile, Q&A und Wikitext |
| **🔍 Volltextsuche** | Sekundengenaue Transkript-Segment-Suche mit Deep Links (`GET /api/search/transcripts`) |
| **💾 Export-Formate** | JSON, CSV, Markdown, MediaWiki-Wikitext, Wikipedia-Vorlage (`.txt`), Gemtext (`.gmi`), Gophermap |
| **🪐 Dual-Space** | Geminispace Kapseln + abonnierbarer Feed (`feed.gmi`) und Gopherspace RFC-1436 Menüs |
| **🎨 Web Frontend** | Bootstrap 5 Dark Mode, komplett lokal gebündelt (`/static/vendor/`), ohne externe CDNs |
| **🛡️ Sicherheit** | SSRF-Filterung (RFC 1918 / Cloud Metadata Block), CSP (`default-src 'self'`), Non-Root Docker Container |

---

## 🏛️ Systemarchitektur

Das System ist in 4 klar getrennte Schichten unterteilt (siehe [`.agents/ARCHITECTURE.md`](.agents/ARCHITECTURE.md)):

```mermaid
graph TD
    UI["Schicht 1: Web-Frontend (Bootstrap 5 Dark Mode & Vanilla JS)"]
    API["FastAPI Backend (Security Headers, CSP, SSRF-Validation)"]
    
    subgraph "Schicht 3: Scraper- & KI-Engine"
        Factory["ScraperFactory"]
        YT["YouTubeScraper (yt-dlp Python-API, Transcript-API)"]
        RSS["RSSScraper (defusedxml, feedparser, Apple Lookup)"]
        Gemini["GeminiAIService (google-genai, Wiki-Templates, Chunking)"]
    end
    
    subgraph "Schicht 4: Persistenz & Exporte"
        ORM["SQLAlchemy 2.0 Async"]
        DB[("PostgreSQL 16 / SQLite")]
        Pub["WebspacePublisher (public/gemini & public/gopher)"]
    end
    
    UI -->|"REST / JSON"| API
    API --> Factory
    Factory --> YT
    Factory --> RSS
    API --> Gemini
    API --> ORM
    ORM --> DB
    API --> Pub
```

---

## 🚀 Schnelleinstieg & Installation

### Option A: Mit Docker Compose (Empfohlen)

Startet die Web-Applikation zusammen mit einer isolierten PostgreSQL-16-Datenbank:

```bash
# 1. Repository klonen
git clone https://github.com/Smeeth/podcast-scraper-for-the-geminispace.git
cd "podcast scraper for the geminispace"

# 2. Konfiguration anlegen (Gemini API-Key optional)
cp .env.example .env

# 3. Stack starten
docker compose up --build
```

Die Weboberfläche steht nun unter **[http://localhost:8000](http://localhost:8000)** bereit.

---

### Option B: Lokale Python-Entwicklung

Für Entwickler, die den Server ohne Container ausführen möchten:

```bash
# 1. Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv

# Unter Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Unter Linux / macOS:
source .venv/bin/activate

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Server starten (Standardmäßig SQLite-Modus, falls kein PostgreSQL konfiguriert ist)
uvicorn app.main:app --reload --port 8000
```

---

## ⚙️ Konfiguration (`.env`)

Alle Einstellungen werden über standardisierte Umgebungsvariablen gesteuert:

```env
# Server & Sicherheit
HOST=0.0.0.0
PORT=8000
DEBUG=false
ALLOWED_ORIGINS=*

# Datenbank (PostgreSQL oder lokales SQLite)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/podcast_db
# Alternativ SQLite für lokale Tests:
# DATABASE_URL=sqlite+aiosqlite:///./podcast_researcher.db

# Google Gemini KI (Optional für KI-Analysen & Wikipedia-Synthese)
GEMINI_API_KEY=AIzaSy...DeinSchluessel
GEMINI_MODEL=gemini-2.5-flash

# Webspace Publisher Pfade
GEMINI_OUTPUT_DIR=public/gemini
GOPHER_OUTPUT_DIR=public/gopher
GOPHER_HOST=gopher.example.org
GOPHER_PORT=70
```

---

## 🪐 Geminispace & Gopherspace Hosting

Die erzeugten Kapsel-Dateien können direkt mit gängigen Daemons ausgeliefert werden:

1. **Gemini Server (z. B. Agate, Molly-Brown):**

   ```bash
   agate --content public/gemini/ --hostname mein-gemini-server.de
   ```

2. **Gopher Server (z. B. Geomyidae, Gophernicus):**

   ```bash
   geomyidae -d public/gopher/ -p 70 -h mein-gopher-server.de
   ```

---

## 🧪 Qualitätssicherung & Verifikation

Das Projekt verfügt über eine umfassende Test- und Verifikations-Suite:

```bash

# 1. SPDX-Header aller Quelldateien prüfen
python .github/scripts/verify_spdx_headers.py

# 2. Sicherheits-Audit (SSRF, defusedxml, Zero Secrets)
python .github/scripts/security_audit.py

# 3. Gemtext- & Gophermap-Validierung
python .github/scripts/gemtext_validator.py

# 4. Automatisierte Tests ausführen (31 Tests)
python -m unittest discover -s tests -p "test_*.py" -v

# 5. Code-Qualität & Linting
ruff check app tests .github/scripts
```

---

## 📚 Living Agent Documentation (`.agents/`)

Die Entwicklungsrichtlinien und Architektur-Entscheidungen werden im Verzeichnis [`.agents/`](.agents/) gepflegt:

- [`.agents/ARCHITECTURE.md`](.agents/ARCHITECTURE.md): Detaillierte Modulübersicht und Datenflüsse.
- [`.agents/CONTEXT.md`](.agents/CONTEXT.md): Status, Kontext und Roadmap.
- **Architectural Decision Records (`.agents/DECISIONS/`):**
  - [ADR-0001: Security First Principle](.agents/DECISIONS/ADR-0001-security-first.md)
  - [ADR-0002: Modular Scraper Adapter Pattern](.agents/DECISIONS/ADR-0002-modular-scraper-adapter.md)
  - [ADR-0003: Single-File Git Commits in English](.agents/DECISIONS/ADR-0003-single-file-commits.md)
  - [ADR-0004: Explicit Unabbreviated File Extensions](.agents/DECISIONS/ADR-0004-unabbreviated-file-extensions.md)
  - [ADR-0005: Two-Step Probe, Zero-Media Storage & Wikipedia Synthesis](.agents/DECISIONS/ADR-0005-two-step-probe-and-wikipedia-synthesis.md)

---

## 📄 Lizenz

Dieses Projekt steht unter der **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.  
Details siehe [LICENSE](LICENSE).

```text
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```
