# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class ChapterDTO:
    title: str
    start_time: float
    start_time_formatted: str = ""

    def __post_init__(self):
        if not self.start_time_formatted:
            hours = int(self.start_time // 3600)
            minutes = int((self.start_time % 3600) // 60)
            seconds = int(self.start_time % 60)
            if hours > 0:
                self.start_time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                self.start_time_formatted = f"{minutes:02d}:{seconds:02d}"


@dataclass
class TranscriptSegmentDTO:
    start: float
    duration: float
    text: str


@dataclass
class TranscriptDTO:
    language: str
    full_text: str
    segments: List[TranscriptSegmentDTO] = field(default_factory=list)


@dataclass
class EpisodeDTO:
    external_id: str
    title: str
    episode_number: Optional[int] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    description: Optional[str] = ""
    audio_or_video_url: Optional[str] = None
    chapters: List[ChapterDTO] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    transcript: Optional[TranscriptDTO] = None


@dataclass
class PodcastDTO:
    platform: str  # 'youtube', 'rss', 'apple'
    title: str
    url: str
    feed_url: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    episodes: List[EpisodeDTO] = field(default_factory=list)


class ScraperException(Exception):
    """Basis-Ausnahme für Scraper-Fehler."""
    pass


class BaseScraper(ABC):
    """
    Abstrakte Basisklasse für Plattform-Scraper (ADR-0002).
    """

    @abstractmethod
    async def extract_podcast_and_episodes(
        self,
        url: str,
        limit: int = 50,
        fetch_transcripts: bool = False
    ) -> PodcastDTO:
        """
        Extrahiert Metadaten des Kanals/Feeds und der zugehörigen Episoden.
        """
        pass

    @abstractmethod
    async def extract_transcript(self, episode_external_id_or_url: str) -> Optional[TranscriptDTO]:
        """
        Extrahiert das Transkript für eine spezifische Episode.
        """
        pass
