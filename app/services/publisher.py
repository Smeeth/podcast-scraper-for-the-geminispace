# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Webspace Publisher Service für Geminispace (public/gemini) und Gopherspace (public/gopher).
Generiert statische .gmi- und gophermap-Dateien direkt im Dateisystem.
"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.config import settings
from app.exporters.gemini import (
    generate_gemtext_feed,
    generate_gemtext_index,
    generate_gemtext_podcast,
)
from app.exporters.gopher import generate_gophermap_index, generate_gophermap_podcast
from app.exporters.utils import safe_slug
from app.models import Podcast

logger = logging.getLogger(__name__)


class WebspacePublisher:
    """
    Dienst zur Generierung und Verteilung von Podcast-Archiven
    in die Webspaces `public/gemini` und `public/gopher`.
    """

    def __init__(self, public_dir: Path | str | None = None, base_dir: Path | str | None = None):
        target = public_dir or base_dir or settings.PUBLIC_DIR
        self.public_dir = Path(target)
        self.gemini_dir = self.public_dir / "gemini"
        self.gopher_dir = self.public_dir / "gopher"

    def ensure_directories(self) -> None:
        """Stellt sicher, dass die Ausgabe-Verzeichnisse existieren."""
        self.gemini_dir.mkdir(parents=True, exist_ok=True)
        self.gopher_dir.mkdir(parents=True, exist_ok=True)

    def publish_all(self, podcasts: Sequence[Podcast]) -> dict[str, Any]:
        """
        Generiert alle Gemtext- und Gophermap-Dateien im Zielverzeichnis.
        Gibt eine Zusammenfassung der erstellten Dateien zurück.
        """
        self.ensure_directories()

        gemini_files = []
        gopher_files = []

        # 1. Geminispace: Index (index.gmi) & Feed (feed.gmi)
        gemini_index_content = generate_gemtext_index(podcasts)
        gemini_index_path = self.gemini_dir / "index.gmi"
        gemini_index_path.write_text(gemini_index_content, encoding="utf-8")
        gemini_files.append("index.gmi")

        gemini_feed_content = generate_gemtext_feed(podcasts)
        gemini_feed_path = self.gemini_dir / "feed.gmi"
        gemini_feed_path.write_text(gemini_feed_content, encoding="utf-8")
        gemini_files.append("feed.gmi")


        # 2. Gopherspace: Index (gophermap)
        gopher_index_content = generate_gophermap_index(
            podcasts, host=settings.GOPHER_HOST, port=settings.GOPHER_PORT
        )
        gopher_index_path = self.gopher_dir / "gophermap"
        gopher_index_path.write_text(gopher_index_content, encoding="utf-8")
        gopher_files.append("gophermap")

        # 3. Einzelne Podcast-Seiten
        for p in podcasts:
            slug = safe_slug(p.title, p.id)

            # Gemini Podcast-Seite (<slug>.gmi)
            gmi_content = generate_gemtext_podcast(p)
            gmi_file = self.gemini_dir / f"{slug}.gmi"
            gmi_file.write_text(gmi_content, encoding="utf-8")
            gemini_files.append(f"{slug}.gmi")

            # Gophermap Podcast-Verzeichnis (<slug>/gophermap)
            pod_gopher_dir = self.gopher_dir / slug
            pod_gopher_dir.mkdir(parents=True, exist_ok=True)
            gopher_content = generate_gophermap_podcast(
                p, host=settings.GOPHER_HOST, port=settings.GOPHER_PORT
            )
            pod_gopher_file = pod_gopher_dir / "gophermap"
            pod_gopher_file.write_text(gopher_content, encoding="utf-8")
            gopher_files.append(f"{slug}/gophermap")

        logger.info(
            f"Webspaces erfolgreich publiziert: {len(gemini_files)} Gemini-Dateien, {len(gopher_files)} Gopher-Dateien."
        )

        return {
            "success": True,
            "podcast_count": len(podcasts),
            "gemini_files_count": len(gemini_files),
            "gopher_files_count": len(gopher_files),
            "gemini_directory": str(self.gemini_dir),
            "gopher_directory": str(self.gopher_dir),
            "gemini_index": str(gemini_index_path),
            "gopher_index": str(gopher_index_path),
        }

    def get_status(self) -> dict[str, Any]:
        """Ermittelt den aktuellen Status der publizierten Webspaces."""
        gemini_count = 0
        gopher_count = 0

        if self.gemini_dir.exists():
            gemini_count = len(list(self.gemini_dir.glob("*.gmi")))

        if self.gopher_dir.exists():
            gopher_count = len(list(self.gopher_dir.glob("**/gophermap")))

        return {
            "gemini_directory": str(self.gemini_dir),
            "gopher_directory": str(self.gopher_dir),
            "gemini_exists": self.gemini_dir.exists(),
            "gopher_exists": self.gopher_dir.exists(),
            "gemini_files_count": gemini_count,
            "gopher_files_count": gopher_count,
        }
