# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import logging
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
import httpx
import feedparser
import defusedxml.ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from app.scrapers.base import (
    BaseScraper,
    PodcastDTO,
    EpisodeDTO,
    ChapterDTO,
    TranscriptDTO,
    TranscriptSegmentDTO,
    ScraperException
)
from app.config import settings, is_safe_external_url

logger = logging.getLogger(__name__)

USER_AGENT = "PodcastResearcherBot/1.0 (+https://github.com/podcast-researcher; safe-rss-reader)"
MAX_FEED_BYTES = 20 * 1024 * 1024  # 20 MB Schutzgrenze gegen DoS


class RSSScraper(BaseScraper):
    """
    Gehärteter RSS/Atom & Apple Podcasts Scraper mit defusedxml Schutz vor XXE und XML-Bomben.
    """

    def __init__(self):
        self.client_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html, */*"
        }

    async def _resolve_apple_podcasts_url(self, url: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Löst eine Apple Podcasts URL (z.B. podcasts.apple.com/.../id12345678) über das iTunes Lookup API auf.
        """
        match = re.search(r"id(\d+)", url)
        if not match:
            raise ScraperException("Konnte keine gültige Apple Podcast ID in der URL finden.")

        podcast_id = match.group(1)
        lookup_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.get(lookup_url, headers=self.client_headers)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    raise ScraperException(f"Podcast mit ID {podcast_id} wurde im Apple Directory nicht gefunden.")

                item = results[0]
                feed_url = item.get("feedUrl")
                if not feed_url:
                    raise ScraperException("Apple Podcast Eintrag enthält keine RSS-Feed-URL.")

                return feed_url, item
        except Exception as e:
            logger.error(f"Fehler beim Auflösen des Apple Podcasts {url}: {e}")
            raise ScraperException(f"Apple Podcasts Lookup fehlgeschlagen: {str(e)}")

    def _parse_duration(self, raw_duration: Any) -> Optional[int]:
        """Konvertiert Dauerangaben (Sekunden oder HH:MM:SS) in ganzzahlige Sekunden."""
        if not raw_duration:
            return None
        raw_str = str(raw_duration).strip()
        if raw_str.isdigit():
            return int(raw_str)
        parts = raw_str.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(float(parts[1]))
        except ValueError:
            pass
        return None

    def _parse_chapters_from_text(self, text: str) -> List[ChapterDTO]:
        """Extrahiert Zeitstempel-Kapitelmarken aus Shownotes (inkl. [01:23] und (01:23))."""
        if not text:
            return []
        chapters: List[ChapterDTO] = []
        pattern = re.compile(r"^[\[\(]?(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]?[:\s\-–—]+\s*(.+)$", re.MULTILINE)
        for match in pattern.finditer(text):
            time_str, title = match.group(1), match.group(2).strip()
            parts = [int(p) for p in time_str.split(":")]
            if len(parts) == 2:
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                continue
            chapters.append(ChapterDTO(title=title, start_time=float(seconds), start_time_formatted=time_str))
        return chapters

    async def _fetch_and_defuse_feed_xml(self, feed_url: str) -> str:
        """
        Lädt den XML-Inhalt herunter und validiert ihn über defusedxml gegen XXE / XML-Bomben.
        Sicherheitsverletzungen (DTD, externe Entities, XML-Bomben) werden hart blockiert.
        """
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = await client.get(feed_url, headers=self.client_headers)
            resp.raise_for_status()

            content = resp.content
            if len(content) > MAX_FEED_BYTES:
                raise ScraperException(f"Feed überschreitet Maximalgröße von {MAX_FEED_BYTES / (1024*1024)} MB.")

            # Sicherheitsprüfung mit defusedxml:
            # DefusedXmlException deckt alle sicherheitsrelevanten Fälle ab:
            # DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden, EntityExpansionLimitExceeded
            # Diese werden HART blockiert. Generische ParseError (Atom, Malformed XML) werden weich behandelt.
            try:
                DefusedET.fromstring(content)
            except DefusedXmlException as xml_security_err:
                raise ScraperException(
                    f"Feed enthält sicherheitskritische XML-Konstrukte (XXE/XML-Bomb) und wurde blockiert: "
                    f"{type(xml_security_err).__name__}: {xml_security_err}"
                )
            except Exception:
                # Nicht-sicherheitsrelevante Parser-Fehler (z.B. kein XML-Root, Atom-Feeds):
                # feedparser kann diese Formate eigenständig verarbeiten.
                pass

            return resp.text

    async def extract_podcast_and_episodes(
        self,
        url: str,
        limit: int = 50,
        fetch_transcripts: bool = False
    ) -> PodcastDTO:
        """
        Extrahiert Podcast- und Episodendaten aus einem RSS/Atom-Feed oder Apple Podcasts Link.
        """
        apple_metadata = None
        is_apple = "podcasts.apple.com" in urlparse(url).netloc.lower()

        if is_apple:
            feed_url, apple_metadata = await self._resolve_apple_podcasts_url(url)
            platform_name = "apple"
        else:
            feed_url = url
            platform_name = "rss"

        # XML sicher laden und verifizieren
        xml_text = await self._fetch_and_defuse_feed_xml(feed_url)

        # Feed parsen mit feedparser
        parsed = feedparser.parse(xml_text)
        if parsed.bozo and not parsed.entries:
            raise ScraperException(f"RSS-Feed konnte nicht geparst werden: {parsed.bozo_exception}")

        channel = parsed.feed

        # Podcast-Metadaten
        title = channel.get("title") or (apple_metadata.get("collectionName") if apple_metadata else "Unbekannter Podcast")
        author = channel.get("author") or channel.get("itunes_author") or (apple_metadata.get("artistName") if apple_metadata else "")
        description = channel.get("description") or channel.get("subtitle") or channel.get("summary") or ""
        website_url = channel.get("link") or url

        image_url = None
        if "image" in channel and hasattr(channel.image, "href"):
            image_url = channel.image.href
        elif "itunes_image" in channel:
            image_url = channel.itunes_image
        elif apple_metadata and "artworkUrl600" in apple_metadata:
            image_url = apple_metadata["artworkUrl600"]

        episodes: List[EpisodeDTO] = []
        for idx, entry in enumerate(parsed.entries[:limit], start=1):
            ep_title = entry.get("title", f"Episode {idx}")
            ep_id = entry.get("id") or entry.get("link") or f"ep-{idx}"
            ep_desc = entry.get("summary") or entry.get("description") or ""

            # Content:encoded bevorzugen für vollständige Show Notes
            if "content" in entry and entry.content:
                for c in entry.content:
                    if c.get("value"):
                        ep_desc = c.get("value")
                        break

            # Veröffentlichungsdatum
            published_at = None
            if "published_parsed" in entry and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            # Dauer
            duration = self._parse_duration(entry.get("itunes_duration"))

            # Episodennummer
            ep_num = None
            if "itunes_episode" in entry:
                try:
                    ep_num = int(entry.itunes_episode)
                except ValueError:
                    pass

            # Audio Enclosure URL
            audio_url = None
            if "enclosures" in entry and entry.enclosures:
                for enc in entry.enclosures:
                    if enc.get("href"):
                        audio_url = enc.get("href")
                        break
            if not audio_url and "link" in entry:
                audio_url = entry.link

            # Kapitelmarken
            chapters = self._parse_chapters_from_text(ep_desc)

            # Transkript URL aus Podcast Namespace (falls vorhanden)
            transcript = None
            transcript_url = None
            if "podcast_transcript" in entry:
                transcript_url = entry.podcast_transcript
            elif "podcast_transcripts" in entry and entry.podcast_transcripts:
                transcript_url = entry.podcast_transcripts[0].get("url")

            if fetch_transcripts and transcript_url:
                transcript = await self.extract_transcript(transcript_url)

            episodes.append(EpisodeDTO(
                external_id=ep_id,
                title=ep_title,
                episode_number=ep_num,
                published_at=published_at,
                duration_seconds=duration,
                description=ep_desc,
                audio_or_video_url=audio_url,
                chapters=chapters,
                metadata={
                    "guid": entry.get("id"),
                    "link": entry.get("link"),
                    "transcript_url": transcript_url
                },
                transcript=transcript
            ))

        return PodcastDTO(
            platform=platform_name,
            title=title,
            url=website_url,
            feed_url=feed_url,
            author=author,
            description=description,
            image_url=image_url,
            metadata={
                "language": channel.get("language"),
                "generator": channel.get("generator"),
                "total_feed_entries": len(parsed.entries)
            },
            episodes=episodes
        )

    async def extract_transcript(self, episode_external_id_or_url: str) -> Optional[TranscriptDTO]:
        """
        Lädt ein externes Transkript (z.B. WebVTT, SRT, JSON) herunter.
        Die URL wird vorab gegen SSRF-Angriffe validiert (ADR-0001).
        """
        if not episode_external_id_or_url.startswith("http"):
            return None

        # SSRF-Schutz: Externe Transkript-URLs müssen die Sicherheitsprüfung bestehen
        is_safe, error_msg = is_safe_external_url(episode_external_id_or_url)
        if not is_safe:
            logger.warning(f"Transkript-URL durch SSRF-Filter blockiert: {episode_external_id_or_url} – {error_msg}")
            return None

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.get(episode_external_id_or_url, headers=self.client_headers)
                resp.raise_for_status()
                text = resp.text

                # Einfaches Parsing von WebVTT / Plain Text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_lines = [l for l in lines if not l.startswith("WEBVTT") and "-->" not in l and not l.isdigit()]
                full_text = " ".join(clean_lines)

                return TranscriptDTO(
                    language="de",
                    full_text=full_text,
                    segments=[]
                )
        except Exception as e:
            logger.warning(f"Konnte RSS-Transkript von {episode_external_id_or_url} nicht laden: {e}")
            return None
