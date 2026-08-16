# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Scraper Modulpaket für modulare Medienextraktion.
"""

from app.scrapers.base import (
    BaseScraper,
    ChapterDTO,
    EpisodeDTO,
    PodcastDTO,
    TranscriptDTO,
    TranscriptSegmentDTO,
)
from app.scrapers.factory import ScraperFactory

__all__ = [
    "BaseScraper",
    "PodcastDTO",
    "EpisodeDTO",
    "TranscriptDTO",
    "ChapterDTO",
    "TranscriptSegmentDTO",
    "ScraperFactory",
]
