# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from app.scrapers.base import (
    BaseScraper,
    PodcastDTO,
    EpisodeDTO,
    ChapterDTO,
    TranscriptDTO,
    TranscriptSegmentDTO,
    ScraperException
)
from app.config import settings

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """
    Sicherheitsgehärteter YouTube-Scraper unter Verwendung der Python-API von yt-dlp
    und youtube-transcript-api (keine Shell-Ausführung).
    """

    def __init__(self):
        self.ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "socket_timeout": settings.REQUEST_TIMEOUT_SECONDS,
            "ignoreerrors": True,
            "noplaylist": False,
        }

    def _extract_video_id(self, url: str) -> Optional[str]:
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
            elif parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/")[1].split("/")[0]
            elif parsed.path.startswith("/v/"):
                return parsed.path.split("/v/")[1].split("/")[0]
            elif parsed.path.startswith("/shorts/"):
                return parsed.path.split("/shorts/")[1].split("/")[0].split("?")[0]
            elif parsed.path.startswith("/live/"):
                return parsed.path.split("/live/")[1].split("/")[0].split("?")[0]
        # Regex Fallback
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    def _parse_chapters_from_description(self, description: str) -> List[ChapterDTO]:
        """Extrahiert Kapitelmarken aus Show Notes (z.B. 01:23 Thema A, [01:23] Thema B, (01:23) - Thema C)."""
        if not description:
            return []
        chapters: List[ChapterDTO] = []
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

    def _fetch_yt_info(self, url: str) -> Dict[str, Any]:
        """Synchroner yt-dlp Extraktionsaufruf zur Ausführung in ThreadPool."""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

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
            raise ScraperException(f"YouTube-Daten konnten nicht geladen werden: {str(e)}")

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
                try:
                    pub_date = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

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
        episodes: List[EpisodeDTO] = []

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
                try:
                    pub_date = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

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

    async def extract_transcript(self, episode_external_id_or_url: str) -> Optional[TranscriptDTO]:
        """
        Lädt Zeitstempel-Segmente und Volltext via youtube-transcript-api.
        """
        video_id = self._extract_video_id(episode_external_id_or_url) or episode_external_id_or_url
        if not video_id or len(video_id) != 11:
            return None

        def _get_transcript_sync() -> Optional[TranscriptDTO]:
            try:
                # Bevorzugte Sprachen: Deutsch, Englisch
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Versuche manuell erstellte oder automatisch generierte Transkripte zu finden
                try:
                    t = transcript_list.find_transcript(["de", "de-DE", "en", "en-US", "en-GB"])
                except Exception:
                    # Fallback auf erstes verfügbares Transkript
                    t = next(iter(transcript_list))

                raw_segments = t.fetch()
                segments: List[TranscriptSegmentDTO] = []
                full_text_parts: List[str] = []

                for item in raw_segments:
                    # youtube-transcript-api v0.6.x returns dicts; v1.x returns FetchedTranscriptSnippet objects.
                    # Support both interfaces via hasattr detection.
                    if hasattr(item, 'text'):
                        text = (item.text or "").strip()
                        start = float(item.start or 0)
                        duration = float(item.duration or 0)
                    else:
                        text = (item.get("text") or "").strip()
                        start = float(item.get("start") or 0)
                        duration = float(item.get("duration") or 0)
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
