# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import contextlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import defusedxml.ElementTree as DefusedET
import feedparser
import httpx
from defusedxml.common import DefusedXmlException

from app.config import (
    is_safe_external_url,
    sanitize_log_message,
    settings,
    validate_and_reconstruct_safe_url,
)
from app.scrapers.base import (
    BaseScraper,
    ChapterDTO,
    EpisodeDTO,
    PodcastDTO,
    ProbeResultDTO,
    ScraperException,
    TranscriptDTO,
)

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

    async def probe_feed(self, url: str) -> ProbeResultDTO:
        """
        Führt eine Vorab-Prüfung eines RSS-, Atom- oder Apple Podcast-Feeds durch (ADR-0005).
        """
        feed_url = url
        apple_metadata = None
        platform = "rss"

        parsed_probe_url = urlparse(url)
        probe_host = (parsed_probe_url.hostname or "").lower()
        if probe_host in ("podcasts.apple.com", "itunes.apple.com") or probe_host.endswith(".apple.com"):
            platform = "apple"
            feed_url, apple_metadata = await self._resolve_apple_podcasts_url(url)

        # SSRF Validierung & URL-Rekonstruktion (CodeQL Taint-Barrier)
        is_safe, error_reason, safe_url = validate_and_reconstruct_safe_url(feed_url)
        if not is_safe:
            raise ScraperException(f"Sicherheitsblockade (SSRF): {error_reason}")

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(safe_url, headers=self.client_headers)
                resp.raise_for_status()
                content = resp.text
        except Exception as e:
            safe_feed = sanitize_log_message(safe_url)
            logger.error("Fehler beim Probe-Download von %s: %s", safe_feed, e)
            raise ScraperException(f"Feed konnte nicht geladen werden: {e}") from e

        try:
            DefusedET.fromstring(content.encode("utf-8"))
        except (DefusedXmlException, Exception) as e:
            raise ScraperException(f"XML-Sicherheitsprüfung für Feed fehlgeschlagen: {e}") from e

        parsed = feedparser.parse(content)
        channel = getattr(parsed, "feed", {})
        title = channel.get("title") or "Unbekannter Podcast" if isinstance(channel, dict) else (getattr(channel, "title", None) or "Unbekannter Podcast")
        author = channel.get("author") if isinstance(channel, dict) else getattr(channel, "author", None)
        if not author and apple_metadata and "artistName" in apple_metadata:
            author = apple_metadata["artistName"]

        description = channel.get("description") or channel.get("subtitle") if isinstance(channel, dict) else (getattr(channel, "description", None) or getattr(channel, "subtitle", None))
        if description:
            description = str(description)[:500]

        image_url = None
        if isinstance(channel, dict):
            img = channel.get("image")
            if isinstance(img, dict) and "href" in img:
                image_url = str(img["href"])
            elif img is not None and hasattr(img, "href"):
                image_url = str(getattr(img, "href", ""))
        else:
            ch_img = getattr(channel, "image", None)
            if ch_img and hasattr(ch_img, "href"):
                image_url = str(getattr(ch_img, "href", ""))
        if not image_url and apple_metadata and "artworkUrl600" in apple_metadata:
            image_url = str(apple_metadata["artworkUrl600"])

        entries = getattr(parsed, "entries", [])
        approx_count = len(entries) if entries else None

        return ProbeResultDTO(
            platform=platform,
            title=str(title),
            url=url,
            author=str(author) if author else None,
            description=str(description) if description else None,
            image_url=image_url,
            approx_episodes_count=approx_count,
            metadata={
                "feed_url": feed_url,
                "language": channel.get("language") if isinstance(channel, dict) else getattr(channel, "language", None),
            }
        )


    async def _resolve_apple_podcasts_url(self, url: str) -> tuple[str, dict[str, Any] | None]:
        """
        Löst eine Apple Podcasts URL (z.B. podcasts.apple.com/.../id12345678) über das iTunes Lookup API auf.
        """
        match = re.search(r"id(\d+)", url)
        if not match:
            raise ScraperException("Konnte keine gültige Apple Podcast ID in der URL finden.")

        podcast_id = match.group(1)
        if not podcast_id.isdigit():
            raise ScraperException("Ungültige Apple Podcast ID.")

        lookup_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
        is_safe, error_msg = is_safe_external_url(lookup_url)
        if not is_safe:
            raise ScraperException(f"Sicherheitsblockade (SSRF) für Apple Lookup: {error_msg}")

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

                safe_feed = sanitize_log_message(feed_url)
                logger.info("Apple Podcast aufgelöst: Feed-URL %s", safe_feed)
                return feed_url, item
        except Exception as e:
            safe_url = sanitize_log_message(url)
            logger.error("Fehler beim Auflösen des Apple Podcasts %s: %s", safe_url, e)
            raise ScraperException(f"Apple Podcasts Lookup fehlgeschlagen: {str(e)}") from e

    def _parse_duration(self, raw_duration: Any) -> int | None:
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
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(float(parts[1]))
        except (ValueError, TypeError):
            # Ungültiges Zeitformat (z.B. nicht-numerische Zeichen in Millisekunden) ignorieren
            pass
        return None

    def _parse_chapters_from_text(self, text: str) -> list[ChapterDTO]:
        """Extrahiert Zeitstempel-Kapitelmarken aus Shownotes (inkl. [01:23] und (01:23))."""
        if not text:
            return []
        chapters: list[ChapterDTO] = []
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
        # SSRF Validierung & URL-Rekonstruktion (CodeQL Taint-Barrier)
        is_safe, error_reason, safe_url = validate_and_reconstruct_safe_url(feed_url)
        if not is_safe:
            raise ScraperException(f"Sicherheitsblockade (SSRF): {error_reason}")

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = await client.get(safe_url, headers=self.client_headers)
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
                ) from xml_security_err
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
        parsed_target_url = urlparse(url)
        target_host = (parsed_target_url.hostname or "").lower()
        is_apple = target_host in ("podcasts.apple.com", "itunes.apple.com") or target_host.endswith(".apple.com")

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

        channel = getattr(parsed, "feed", {}) or {}

        # Podcast-Metadaten
        channel_title = channel.get("title") if isinstance(channel, dict) else getattr(channel, "title", None)
        title: str = str(channel_title or (apple_metadata.get("collectionName") if apple_metadata else "Unbekannter Podcast") or "Unbekannter Podcast")
        author = str(channel.get("author", "") or channel.get("itunes_author", "") if isinstance(channel, dict) else (apple_metadata.get("artistName", "") if apple_metadata else ""))
        description = str(channel.get("description", "") or channel.get("subtitle", "") or channel.get("summary", "") if isinstance(channel, dict) else "")
        website_url = str(channel.get("link", url) if isinstance(channel, dict) else url)

        image_url = None
        if isinstance(channel, dict):
            img = channel.get("image")
            if isinstance(img, dict) and "href" in img:
                image_url = str(img["href"])
            elif img is not None and hasattr(img, "href"):
                image_url = str(getattr(img, "href", ""))  # noqa: B009
            elif "itunes_image" in channel:
                image_url = str(channel.get("itunes_image"))
        else:
            if hasattr(channel, "image") and hasattr(channel.image, "href"):
                image_url = str(channel.image.href)
            elif hasattr(channel, "itunes_image"):
                image_url = str(channel.itunes_image)
        if not image_url and apple_metadata and "artworkUrl600" in apple_metadata:
            image_url = str(apple_metadata["artworkUrl600"])

        episodes: list[EpisodeDTO] = []
        entries: list[Any] = list(getattr(parsed, "entries", []))
        for idx, entry in enumerate(entries[:limit], start=1):
            ep_title = str(entry.get("title") if isinstance(entry, dict) else (getattr(entry, "title", None) or f"Episode {idx}"))
            raw_id = entry.get("id") or entry.get("link") if isinstance(entry, dict) else (getattr(entry, "id", None) or getattr(entry, "link", None))
            ep_id = str(raw_id or f"ep-{idx}")
            raw_desc = entry.get("summary") or entry.get("description") if isinstance(entry, dict) else (getattr(entry, "summary", None) or getattr(entry, "description", None))
            ep_desc = str(raw_desc or "")

            # Content:encoded bevorzugen für vollständige Show Notes
            entry_content = entry.get("content") if isinstance(entry, dict) else getattr(entry, "content", None)
            if entry_content and isinstance(entry_content, list):
                for c in entry_content:
                    c_val = c.get("value") if isinstance(c, dict) else getattr(c, "value", None)
                    if c_val:
                        ep_desc = str(c_val)
                        break

            # Veröffentlichungsdatum
            published_at = None
            pub_parsed = entry.get("published_parsed") if isinstance(entry, dict) else getattr(entry, "published_parsed", None)
            if pub_parsed and hasattr(pub_parsed, "__getitem__"):
                with contextlib.suppress(Exception):
                    published_at = datetime(
                        int(pub_parsed[0]),
                        int(pub_parsed[1]),
                        int(pub_parsed[2]),
                        int(pub_parsed[3]),
                        int(pub_parsed[4]),
                        int(pub_parsed[5]),
                        tzinfo=UTC,
                    )

            # Dauer
            raw_dur = entry.get("itunes_duration") if isinstance(entry, dict) else getattr(entry, "itunes_duration", None)
            duration = self._parse_duration(str(raw_dur) if raw_dur is not None else None)

            # Episodennummer
            ep_num = None
            raw_ep_num = entry.get("itunes_episode") if isinstance(entry, dict) else getattr(entry, "itunes_episode", None)
            if raw_ep_num is not None:
                with contextlib.suppress(ValueError, TypeError):
                    ep_num = int(raw_ep_num)

            # Audio Enclosure URL
            audio_url: str | None = None
            enclosures = entry.get("enclosures") if isinstance(entry, dict) else getattr(entry, "enclosures", None)
            if enclosures and isinstance(enclosures, list):
                for enc in enclosures:
                    enc_href = enc.get("href") if isinstance(enc, dict) else getattr(enc, "href", None)
                    if enc_href:
                        audio_url = str(enc_href)
                        break
            if not audio_url:
                raw_link = entry.get("link") if isinstance(entry, dict) else getattr(entry, "link", None)
                if raw_link:
                    audio_url = str(raw_link)

            # Kapitelmarken
            chapters = self._parse_chapters_from_text(ep_desc)

            # Transkript URL aus Podcast Namespace (falls vorhanden)
            transcript = None
            transcript_url: str | None = None
            raw_t_url = entry.get("podcast_transcript") if isinstance(entry, dict) else getattr(entry, "podcast_transcript", None)
            if raw_t_url:
                transcript_url = str(raw_t_url)
            else:
                pts = entry.get("podcast_transcripts") if isinstance(entry, dict) else getattr(entry, "podcast_transcripts", None)
                if pts and isinstance(pts, list) and len(pts) > 0:
                    first_pt = pts[0]
                    first_url = first_pt.get("url") if isinstance(first_pt, dict) else getattr(first_pt, "url", None)
                    if first_url:
                        transcript_url = str(first_url)

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
                    "guid": entry.get("id") if isinstance(entry, dict) else getattr(entry, "id", None),
                    "link": entry.get("link") if isinstance(entry, dict) else getattr(entry, "link", None),
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
                "language": channel.get("language") if isinstance(channel, dict) else getattr(channel, "language", None),
                "generator": channel.get("generator") if isinstance(channel, dict) else getattr(channel, "generator", None),
                "total_feed_entries": len(parsed.entries)
            },
            episodes=episodes
        )

    async def extract_transcript(self, episode_external_id_or_url: str) -> TranscriptDTO | None:
        """
        Lädt ein externes Transkript (z.B. WebVTT, SRT, JSON) herunter.
        Die URL wird vorab gegen SSRF-Angriffe validiert (ADR-0001).
        """
        if not episode_external_id_or_url.startswith("http"):
            return None

        # SSRF-Schutz: Externe Transkript-URLs müssen die Sicherheitsprüfung bestehen
        is_safe, error_msg = is_safe_external_url(episode_external_id_or_url)
        if not is_safe:
            safe_t_url = sanitize_log_message(episode_external_id_or_url)
            logger.warning("Transkript-URL durch SSRF-Filter blockiert: %s – %s", safe_t_url, error_msg)
            return None

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                resp = await client.get(episode_external_id_or_url, headers=self.client_headers)
                resp.raise_for_status()
                text = resp.text

                # Einfaches Parsing von WebVTT / Plain Text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_lines = [line_item for line_item in lines if not line_item.startswith("WEBVTT") and "-->" not in line_item and not line_item.isdigit()]
                full_text = " ".join(clean_lines)

                return TranscriptDTO(
                    language="de",
                    full_text=full_text,
                    segments=[]
                )
        except Exception as e:
            safe_t_url = sanitize_log_message(episode_external_id_or_url)
            logger.warning("Konnte RSS-Transkript von %s nicht laden: %s", safe_t_url, e)
            return None
