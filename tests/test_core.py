# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import unittest
from datetime import UTC

from app.config import is_safe_external_url
from app.schemas import AIAnalysisRequest, ScrapeRequest
from app.scrapers.factory import ScraperFactory
from app.scrapers.rss import RSSScraper
from app.scrapers.youtube import YouTubeScraper


class TestSecurityAndSSRF(unittest.TestCase):
    """Testet die SSRF-Filterung (ADR-0001)."""

    def test_ssrf_blocked_ips(self):
        blocked_urls = [
            "http://127.0.0.1/admin",
            "http://localhost:8000/feed",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/internal.xml",
            "http://192.168.1.1/feed.rss",
            "http://172.16.0.5/api",
            "ftp://example.com/feed.xml",
            "file:///etc/passwd",
            "gopher://example.com/",
        ]
        for url in blocked_urls:
            is_safe, msg = is_safe_external_url(url)
            self.assertFalse(is_safe, f"URL {url} sollte als unsicher geblockt werden! Grund: {msg}")

    def test_valid_public_urls(self):
        valid_urls = [
            "https://www.youtube.com/@Tagesschau",
            "https://www.youtube.com/playlist?list=PL3ZX4mHhK0U9XGzJd_6",
            "https://podcasts.apple.com/de/podcast/der-tag/id123456789",
            "https://feeds.br.de/radiowissen/feed.xml",
        ]
        for url in valid_urls:
            is_safe, msg = is_safe_external_url(url)
            self.assertTrue(is_safe, f"Gültige URL {url} wurde fälschlicherweise geblockt: {msg}")


    def test_ssrf_evasion_techniques(self):
        """Testet erweiterte SSRF-Evasion-Techniken wie DWORD, Hex, Oktal und IPv6."""
        evasion_urls = [
            "http://2130706433/admin",           # DWORD Notation für 127.0.0.1
            "http://0x7f000001/admin",          # Hex Notation für 127.0.0.1
            "http://0177.0.0.1/admin",           # Oktal Notation für 127.0.0.1
            "http://2852039166/latest",          # DWORD Notation für 169.254.169.254
            "http://[::1]/internal",             # IPv6 Loopback
            "http://[::ffff:127.0.0.1]/",        # IPv4-mapped IPv6
            "http://metadata.google.internal/",  # Cloud Metadata
        ]
        for url in evasion_urls:
            is_safe, msg = is_safe_external_url(url)
            self.assertFalse(is_safe, f"Evasion-URL {url} sollte als unsicher geblockt werden! ({msg})")


class TestScraperFactory(unittest.TestCase):
    """Testet die Plattform-Erkennung der ScraperFactory (ADR-0002)."""

    def test_detect_youtube(self):
        yt_urls = [
            "https://www.youtube.com/@Kanal",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PL123456",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ]
        for url in yt_urls:
            platform = ScraperFactory.detect_platform(url)
            self.assertEqual(platform, "youtube")
            scraper = ScraperFactory.get_scraper_for_url(url)
            self.assertIsInstance(scraper, YouTubeScraper)

    def test_detect_apple(self):
        apple_url = "https://podcasts.apple.com/de/podcast/beispiel-podcast/id123456789"
        platform = ScraperFactory.detect_platform(apple_url)
        self.assertEqual(platform, "apple")
        scraper = ScraperFactory.get_scraper_for_url(apple_url)
        self.assertIsInstance(scraper, RSSScraper)

    def test_detect_rss(self):
        rss_url = "https://example.com/podcast/feed.xml"
        platform = ScraperFactory.detect_platform(rss_url)
        self.assertEqual(platform, "rss")
        scraper = ScraperFactory.get_scraper_for_url(rss_url)
        self.assertIsInstance(scraper, RSSScraper)


class TestYouTubeScraperDetails(unittest.TestCase):
    """Testet Detailfunktionen des YouTube-Scrapers."""

    def test_extract_video_id(self):
        scraper = YouTubeScraper()
        self.assertEqual(scraper._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(scraper._extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(scraper._extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(scraper._extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(scraper._extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_parse_chapters(self):
        scraper = YouTubeScraper()
        desc = (
            "00:00 Intro\n"
            "[01:30] Thema Eins\n"
            "(05:45) - Thema Zwei\n"
            "01:15:00 Schlusswort\n"
        )
        chapters = scraper._parse_chapters_from_description(desc)
        self.assertEqual(len(chapters), 4)
        self.assertEqual(chapters[0].title, "Intro")
        self.assertEqual(chapters[0].start_time, 0.0)
        self.assertEqual(chapters[1].title, "Thema Eins")
        self.assertEqual(chapters[1].start_time, 90.0)
        self.assertEqual(chapters[2].title, "Thema Zwei")
        self.assertEqual(chapters[2].start_time, 345.0)
        self.assertEqual(chapters[3].title, "Schlusswort")
        self.assertEqual(chapters[3].start_time, 4500.0)


class TestRSSScraperDetails(unittest.TestCase):
    """Testet Detailfunktionen des RSS-Scrapers."""

    def test_parse_duration(self):
        scraper = RSSScraper()
        self.assertEqual(scraper._parse_duration("3600"), 3600)
        self.assertEqual(scraper._parse_duration("01:00:00"), 3600)
        self.assertEqual(scraper._parse_duration("45:30"), 2730)
        self.assertIsNone(scraper._parse_duration("invalid"))

    def test_parse_chapters_from_text(self):
        scraper = RSSScraper()
        shownotes = (
            "Hier sind die Kapitelmarken:\n"
            "00:00 Begrüßung\n"
            "[02:15] Hauptthema\n"
            "(10:30): Fazit\n"
        )
        chapters = scraper._parse_chapters_from_text(shownotes)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].title, "Begrüßung")
        self.assertEqual(chapters[1].title, "Hauptthema")
        self.assertEqual(chapters[2].title, "Fazit")


class TestSchemas(unittest.TestCase):
    """Testet die Pydantic v2 Schemas."""

    def test_scrape_request_validation(self):
        # Gültig
        req = ScrapeRequest(url="https://www.youtube.com/@test", limit=25)
        self.assertEqual(req.limit, 25)

        # Ungültig (SSRF)
        with self.assertRaises(ValueError):
            ScrapeRequest(url="http://127.0.0.1/attack")

    def test_ai_analysis_request_validation(self):
        # Gültig
        ai_req = AIAnalysisRequest(podcast_id="pod-123", analysis_type="wikitext_table")
        self.assertEqual(ai_req.analysis_type, "wikitext_table")

        ai_summary = AIAnalysisRequest(podcast_id="pod-123", analysis_type="summary")
        self.assertEqual(ai_summary.analysis_type, "summary")

        # Ungültiger Typ
        with self.assertRaises(ValueError):
            AIAnalysisRequest(podcast_id="pod-123", analysis_type="invalid_action")


class TestGeminiExporter(unittest.TestCase):
    """Testet den Geminispace Exporter (MIME text/gemini)."""

    def setUp(self):
        from datetime import datetime

        from app.models import Episode, Podcast
        self.pod = Podcast(
            id="test-pod-1",
            platform="youtube",
            title="Tech & AI Talk",
            url="https://youtube.com/@techtalk",
            author="Max Mustermann",
            description="Ein wöchentlicher Talk über KI und Open Source Software."
        )
        self.ep = Episode(
            id="test-ep-1",
            podcast_id="test-pod-1",
            external_id="dQw4w9WgXcQ",
            title="Episode 1: Die Zukunft von Open Source",
            episode_number=1,
            published_at=datetime(2026, 1, 15, tzinfo=UTC),
            duration_seconds=3600,
            audio_or_video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
            description="In dieser Folge diskutieren wir GPL-3.0 und Geminispace.",
            chapters=[
                {"title": "Intro", "start_time": 0.0, "start_time_formatted": "00:00"},
                {"title": "GPL Lizenz", "start_time": 300.0, "start_time_formatted": "05:00"}
            ]
        )
        self.pod.episodes = [self.ep]

    def test_generate_gemtext_podcast(self):
        from app.exporters.gemini import generate_gemtext_podcast
        gmi = generate_gemtext_podcast(self.pod)

        # Gemtext-Syntax Validierung
        self.assertIn("# 📻 Tech & AI Talk", gmi)
        self.assertIn("## 📋 Episoden (1 Folgen)", gmi)
        self.assertIn("### #1 Episode 1: Die Zukunft von Open Source", gmi)
        self.assertIn("=> https://youtube.com/watch?v=dQw4w9WgXcQ", gmi)
        self.assertIn("* [00:00] Intro", gmi)
        self.assertIn("* [05:00] GPL Lizenz", gmi)
        self.assertIn("=> index.gmi", gmi)

    def test_generate_gemtext_index(self):
        from app.exporters.gemini import generate_gemtext_index
        index_gmi = generate_gemtext_index([self.pod])

        self.assertIn("# 📻 Podcast & Media Channel Archive (Geminispace)", index_gmi)
        self.assertIn("=> tech_ai_talk.gmi", index_gmi)


class TestGopherExporter(unittest.TestCase):
    """Testet den Gopherspace Exporter (RFC 1436 gophermap)."""

    def setUp(self):
        from app.models import Episode, Podcast
        self.pod = Podcast(
            id="test-pod-2",
            platform="rss",
            title="Gopher & Retro Computing",
            url="https://example.com/podcast",
            author="Gopher Fan",
            description="Kanal über Retro-Protokolle."
        )
        self.ep = Episode(
            id="test-ep-2",
            podcast_id="test-pod-2",
            external_id="ep-2",
            title="Folge 42: Das Gopher Protokoll",
            episode_number=42,
            duration_seconds=1800,
            audio_or_video_url="https://example.com/audio/ep42.mp3",
            chapters=[{"title": "RFC 1436", "start_time": 60.0, "start_time_formatted": "01:00"}]
        )
        self.pod.episodes = [self.ep]

    def test_generate_gophermap_podcast(self):
        from app.exporters.gopher import generate_gophermap_podcast
        gopher = generate_gophermap_podcast(self.pod, host="gopher.example.org", port=70)

        # RFC 1436 Zeilen validieren (jede Zeile muss Typ 'i', 'h', '1' oder '0' haben und 4 Tab-getrennte Felder)
        lines = [line_item for line_item in gopher.splitlines() if line_item.strip()]
        for line in lines:
            parts = line.split("\t")
            self.assertEqual(len(parts), 4, f"Ungültige RFC 1436 Gopher-Zeile (braucht 4 Tabs): '{line}'")
            self.assertIn(line[0], ("i", "h", "1", "0", "9"))

        self.assertIn("URL:https://example.com/audio/ep42.mp3", gopher)

    def test_generate_gophermap_index(self):
        from app.exporters.gopher import generate_gophermap_index
        gopher_idx = generate_gophermap_index([self.pod], host="gopher.example.org", port=70)

        self.assertIn("1Gopher & Retro Computing", gopher_idx)
        self.assertIn("/gopher_retro_computing", gopher_idx)


class TestWebspacePublisher(unittest.TestCase):
    """Testet den WebspacePublisher Service und sichere Slug-Generierung."""

    def test_safe_slug(self):
        from app.exporters.utils import safe_slug
        self.assertEqual(safe_slug("Podcast: Hallo Welt!"), "podcast_hallo_welt")
        self.assertEqual(safe_slug("../../etc/passwd"), "etcpasswd")
        self.assertEqual(safe_slug(""), "podcast")

    def test_publish_all_creates_files(self):
        import shutil
        import tempfile
        from pathlib import Path

        from app.models import Episode, Podcast
        from app.services.publisher import WebspacePublisher

        temp_dir = tempfile.mkdtemp()
        try:
            pub = WebspacePublisher(base_dir=temp_dir)
            pod = Podcast(
                id="p1",
                platform="youtube",
                title="Test Publisher",
                url="https://youtube.com/@test"
            )
            pod.episodes = [
                Episode(
                    id="e1",
                    podcast_id="p1",
                    title="Test Ep",
                    audio_or_video_url="https://youtube.com/watch?v=123"
                )
            ]
            result = pub.publish_all([pod])

            self.assertTrue(result["success"])
            self.assertEqual(result["podcast_count"], 1)

            # Prüfen, ob die Dateien existieren
            gemini_dir = Path(temp_dir) / "gemini"
            gopher_dir = Path(temp_dir) / "gopher"

            self.assertTrue((gemini_dir / "index.gmi").exists())
            self.assertTrue((gemini_dir / "test_publisher.gmi").exists())
            self.assertTrue((gopher_dir / "gophermap").exists())
            self.assertTrue((gopher_dir / "test_publisher" / "gophermap").exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
