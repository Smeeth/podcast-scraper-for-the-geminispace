# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import logging
from urllib.parse import urlparse

from app.config import is_safe_external_url, sanitize_log_message
from app.scrapers.base import BaseScraper, ScraperException
from app.scrapers.rss import RSSScraper
from app.scrapers.youtube import YouTubeScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """
    Factory-Klasse zur sicheren Erkennung der Ziel-Plattform und Instanziierung
    des entsprechenden Scrapers (ADR-0002).
    """

    @staticmethod
    def detect_platform(url: str) -> str:
        """
        Ermittelt die Plattform basierend auf der URL.
        Rückgabe: 'youtube', 'apple' oder 'rss'.
        """
        if not url:
            raise ScraperException("Keine URL angegeben.")

        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()

        if (
            hostname in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be")
            or hostname.endswith(".youtube.com")
            or hostname.endswith(".youtu.be")
        ):
            return "youtube"
        if hostname in ("podcasts.apple.com", "itunes.apple.com") or hostname.endswith(".apple.com"):
            return "apple"
        return "rss"

    @classmethod
    def get_scraper_for_url(cls, url: str) -> BaseScraper:
        """
        Validiert die URL sicher gegen SSRF und liefert die passende Scraper-Instanz.
        """
        is_safe, error_msg = is_safe_external_url(url)
        if not is_safe:
            raise ScraperException(f"URL durch Sicherheitsfilter blockiert: {error_msg}")

        platform = cls.detect_platform(url)
        safe_url = sanitize_log_message(url)

        if platform == "youtube":
            logger.info("Plattform erkannt: YouTube (%s)", safe_url)
            return YouTubeScraper()
        if platform in ("apple", "rss"):
            logger.info("Plattform erkannt: %s (%s)", platform.upper(), safe_url)
            return RSSScraper()
        raise ScraperException(f"Kein Scraper für Plattform '{platform}' verfügbar.")
