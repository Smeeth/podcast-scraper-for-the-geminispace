# ADR-0002: Modulares Scraper-Adapter-Pattern

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

## Status
Akzeptiert

## Kontext
Die Anwendung soll flexibel unterschiedliche Plattformen (YouTube-Kanäle, Playlists, RSS-Feeds, Apple Podcasts, Spotify-Feeds etc.) unterstützen. Jede Plattform besitzt unterschiedliche Protokolle, Metadaten-Formate und Methoden zur Bereitstellung von Episoden und Transkripten.

## Entscheidung
Wir implementieren das **Adapter- / Factory-Pattern** im Modul `app/scrapers/`:

1. **`BaseScraper` (Abstrakte Basisklasse):**
   - Definiert die einheitliche Schnittstelle:
     - `extract_podcast_info(url: str) -> PodcastInfo`
     - `extract_episodes(url: str, limit: int = 50) -> List[EpisodeInfo]`
     - `extract_transcript(external_id_or_url: str) -> Optional[TranscriptInfo]`
   - Typisierte Data-Transfer-Objects (DTOs) via Pydantic / Dataclasses stellen plattformunabhängige Datenstrukturen sicher.

2. **`ScraperFactory`:**
   - Analysiert die URL, validiert das Format und instanziiert den passenden Adapter (`YouTubeScraper`, `RSSScraper`).
   - Wirft bei unbekannten oder unzulässigen Plattformen/URLs eine kontrollierte `ScraperValidationError`.

3. **Plattform-Adapter:**
   - `YouTubeScraper`: Nutzt `yt-dlp` (Python-API) für Kanal-, Playlist- und Episoden-Metadaten sowie `youtube-transcript-api` für Untertitel.
   - `RSSScraper`: Verarbeitet Standard-RSS 2.0 / Atom-Feeds mit Namespace-Support (`itunes:*`, `podcast:*`, `content:*`) und bindet den Apple Podcasts iTunes Lookup Service ein.

## Konsequenzen
- **Vorteile:**
  - Hohe Modularität und einfache Erweiterbarkeit um weitere Medienplattformen (z. B. SoundCloud, Vimeo).
  - Saubere Trennung von Scraping-Logik, Business-Logik und Datenbank-Persistenz.
  - Vollständige Testbarkeit der einzelnen Scraper über Mocks und Test-Feeds.
- **Trade-offs:**
  - Jede neue Plattform erfordert die Implementierung der Schnittstellen-Methoden und DTO-Mappings.
