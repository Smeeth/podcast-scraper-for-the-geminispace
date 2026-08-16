# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import asyncio
import contextlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

from app.config import settings
from app.scrapers.base import (
    BaseScraper,
    ChapterDTO,
    EpisodeDTO,
    PodcastDTO,
    ProbeResultDTO,
    ScraperException,
    TranscriptDTO,
    TranscriptSegmentDTO,
)

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """
    Sicherheitsgehärteter YouTube-Scraper unter Verwendung der Python-API von yt-dlp
    und youtube-transcript-api (keine Shell-Ausführung).
    """

    def __init__(self):
        self.ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "socket_timeout": settings.REQUEST_TIMEOUT_SECONDS,
            "ignoreerrors": True,
            "noplaylist": False,
        }

    async def probe_feed(self, url: str) -> ProbeResultDTO:
        """
        Führt eine blitzschnelle Vorab-Prüfung von YouTube-Kanälen, Playlists oder Videos durch (< 1s).
        """
        probe_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlist_items": "0",
            "socket_timeout": 10,
            "ignoreerrors": True,
        }

        def _fetch_probe():
            with yt_dlp.YoutubeDL(probe_opts) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(url, download=False)
                return dict(info) if isinstance(info, dict) else {}

        try:
            info = await asyncio.to_thread(_fetch_probe)
        except Exception as e:
            logger.error(f"Fehler bei YouTube Probe für {url}: {e}")
            raise ScraperException(f"YouTube-Kanal konnte nicht geprüft werden: {e}") from e

        if not info:
            raise ScraperException("Keine Kanalinformationen von YouTube erhalten.")

        title = info.get("channel") or info.get("uploader") or info.get("title") or "YouTube Kanal"
        author = info.get("uploader") or info.get("channel") or "Unbekannt"
        description = (info.get("description") or "")[:500]

        thumbnails = info.get("thumbnails") or []
        image_url = thumbnails[-1].get("url") if thumbnails else info.get("thumbnail")

        approx_count = info.get("playlist_count")
        if approx_count is None and "entries" in info:
            entries = info.get("entries")
            approx_count = len(entries) if entries else None

        return ProbeResultDTO(
            platform="youtube",
            title=title,
            url=url,
            author=author,
            description=description,
            image_url=image_url,
            approx_episodes_count=approx_count,
            metadata={
                "channel_id": info.get("channel_id"),
                "channel_url": info.get("channel_url"),
                "subscriber_count": info.get("subscriber_count"),
            }
        )


    def _extract_video_id(self, url: str) -> str | None:
        """Extrahiert sicher die 11-stellige Video-ID aus einer YouTube-URL."""
        if not url:
            return None
        parsed = urlparse(url)
        if parsed.hostname in ("youtu.be", "www.youtu.be"):
            return parsed.path.strip("/")
        if "youtube.com" in (parsed.hostname or ""):
            if parsed.path == "/watch":
                qs = parse_qs(parsed.query)
                return qs.get("v", [None])[0]
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/")[1].split("/")[0]
            if parsed.path.startswith("/v/"):
                return parsed.path.split("/v/")[1].split("/")[0]
            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/shorts/")[1].split("/")[0].split("?")[0]
            if parsed.path.startswith("/live/"):
                return parsed.path.split("/live/")[1].split("/")[0].split("?")[0]
        # Regex Fallback
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    def _parse_chapters_from_description(self, description: str) -> list[ChapterDTO]:
        """Extrahiert Kapitelmarken aus Show Notes (z.B. 01:23 Thema A, [01:23] Thema B, (01:23) - Thema C)."""
        if not description:
            return []
        chapters: list[ChapterDTO] = []
        # Pattern für mm:ss oder hh:mm:ss gefolgt von Text (mit optionalen Klammern [01:23] oder (01:23))
        pattern = re.compile(r"^[\[\(]?(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]?[:\s\-–—]+\s*(.+)$", re.MULTILINE)
        for match in pattern.finditer(description):
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

    def _fetch_yt_info(self, url: str) -> dict[str, Any]:
        """Synchroner yt-dlp Extraktionsaufruf zur Ausführung in ThreadPool."""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:  # type: ignore[arg-type]
            info: Any = ydl.extract_info(url, download=False)
            return dict(info) if isinstance(info, dict) else {}

    async def extract_podcast_and_episodes(
        self,
        url: str,
        limit: int = 50,
        fetch_transcripts: bool = False
    ) -> PodcastDTO:
        """
        Extrahiert Kanal-, Playlist- oder Video-Informationen und wandelt sie in PodcastDTO um.
        """
        try:
            info = await asyncio.to_thread(self._fetch_yt_info, url)
        except Exception as e:
            logger.error(f"Fehler bei YouTube-Extraktion für {url}: {e}")
            raise ScraperException(f"YouTube-Daten konnten nicht geladen werden: {str(e)}") from e

        if not info:
            raise ScraperException("Keine Daten von YouTube empfangen.")

        # Unterscheidung: Einzelvideo vs. Kanal / Playlist
        is_single_video = info.get("_type") != "playlist" and "entries" not in info

        if is_single_video:
            channel_title = info.get("uploader") or info.get("channel") or info.get("title") or "YouTube Media"
            channel_url = info.get("uploader_url") or info.get("channel_url") or url
            channel_desc = info.get("description") or ""
            channel_thumbnail = info.get("thumbnail")

            # Einzelne Episode
            video_id = info.get("id")
            pub_date = None
            upload_date = info.get("upload_date")
            if upload_date and len(upload_date) == 8:
                with contextlib.suppress(ValueError):
                    pub_date = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)

            chapters = []
            if info.get("chapters"):
                for ch in info["chapters"]:
                    chapters.append(ChapterDTO(
                        title=ch.get("title", "Kapitel"),
                        start_time=float(ch.get("start_time", 0))
                    ))
            else:
                chapters = self._parse_chapters_from_description(info.get("description", ""))

            transcript = None
            if fetch_transcripts and video_id:
                transcript = await self.extract_transcript(video_id)

            episode = EpisodeDTO(
                external_id=video_id or "unknown",
                title=info.get("title", "Unbekanntes Video"),
                episode_number=1,
                published_at=pub_date,
                duration_seconds=int(info.get("duration") or 0),
                description=info.get("description", ""),
                audio_or_video_url=info.get("webpage_url") or url,
                chapters=chapters,
                metadata={
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "tags": info.get("tags", [])
                },
                transcript=transcript
            )

            return PodcastDTO(
                platform="youtube",
                title=channel_title,
                url=channel_url,
                feed_url=url,
                author=info.get("uploader") or info.get("channel"),
                description=channel_desc[:1000],
                image_url=channel_thumbnail,
                metadata={"type": "single_video"},
                episodes=[episode]
            )

        # Playlist oder Kanal
        channel_title = info.get("title") or info.get("uploader") or "YouTube Kanal"
        channel_url = info.get("webpage_url") or info.get("channel_url") or url
        channel_desc = info.get("description") or ""
        thumbnails = info.get("thumbnails") or []
        channel_thumbnail = thumbnails[-1].get("url") if thumbnails else info.get("thumbnail")

        entries = list(info.get("entries") or [])
        episodes: list[EpisodeDTO] = []

        for idx, entry in enumerate(entries[:limit], start=1):
            if not entry:
                continue
            video_id = entry.get("id") or self._extract_video_id(entry.get("url", ""))
            if not video_id:
                continue

            entry_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
            upload_date = entry.get("upload_date")
            pub_date = None
            if upload_date and len(upload_date) == 8:
                with contextlib.suppress(ValueError):
                    pub_date = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)

            desc = entry.get("description") or ""
            chapters = self._parse_chapters_from_description(desc)

            transcript = None
            if fetch_transcripts and video_id:
                transcript = await self.extract_transcript(video_id)

            episodes.append(EpisodeDTO(
                external_id=video_id,
                title=entry.get("title", f"Folge {idx}"),
                episode_number=idx,
                published_at=pub_date,
                duration_seconds=int(entry.get("duration") or 0),
                description=desc,
                audio_or_video_url=entry_url,
                chapters=chapters,
                metadata={
                    "view_count": entry.get("view_count"),
                    "ie_key": entry.get("ie_key")
                },
                transcript=transcript
            ))

        return PodcastDTO(
            platform="youtube",
            title=channel_title,
            url=channel_url,
            feed_url=url,
            author=info.get("uploader") or info.get("channel") or channel_title,
            description=channel_desc[:2000],
            image_url=channel_thumbnail,
            metadata={"total_entries": len(entries)},
            episodes=episodes
        )

    async def extract_transcript(self, episode_external_id_or_url: str) -> TranscriptDTO | None:
        """
        Lädt Zeitstempel-Segmente und Volltext via youtube-transcript-api.
        """
        video_id = self._extract_video_id(episode_external_id_or_url) or episode_external_id_or_url
        if not video_id or len(video_id) != 11:
            return None

        def _get_transcript_sync() -> TranscriptDTO | None:
            try:
                # Bevorzugte Sprachen: Deutsch, Englisch
                if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)  # type: ignore[attr-defined]
                else:
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                # Versuche manuell erstellte oder automatisch generierte Transkripte zu finden
                try:
                    t = transcript_list.find_transcript(["de", "de-DE", "en", "en-US", "en-GB"])
                except Exception:
                    # Fallback auf erstes verfügbares Transkript
                    t = next(iter(transcript_list))

                raw_segments = t.fetch()
                segments: list[TranscriptSegmentDTO] = []
                full_text_parts: list[str] = []

                for item in raw_segments:
                    # youtube-transcript-api v0.6.x returns dicts; v1.x returns FetchedTranscriptSnippet objects.
                    if isinstance(item, dict):
                        text = str(item.get("text", "")).strip()
                        start = float(item.get("start", 0) or 0)
                        duration = float(item.get("duration", 0) or 0)
                    else:
                        text = str(getattr(item, "text", "") or "").strip()
                        start = float(getattr(item, "start", 0) or 0)
                        duration = float(getattr(item, "duration", 0) or 0)
                    if text:
                        segments.append(TranscriptSegmentDTO(
                            start=start,
                            duration=duration,
                            text=text
                        ))
                        full_text_parts.append(text)

                return TranscriptDTO(
                    language=t.language_code,
                    full_text=" ".join(full_text_parts),
                    segments=segments
                )
            except (TranscriptsDisabled, NoTranscriptFound):
                logger.info(f"Kein Transkript verfügbar für YouTube Video {video_id}")
                return None
            except Exception as e:
                logger.warning(f"Fehler beim Abruf des Transkripts für {video_id}: {e}")
                return None

        return await asyncio.to_thread(_get_transcript_sync)
