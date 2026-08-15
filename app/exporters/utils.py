# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Gemeinsame Hilfsfunktionen für Exporter und Webspace-Publisher.
"""

import re


def safe_slug(title: str, fallback_id: str = "podcast") -> str:
    """
    Erzeugt einen sicheren Dateinamen-Slug ohne Pfad-Traversal-Gefahr (ADR-0001).
    Erlaubt nur alphanumerische Zeichen, Bindestriche und Unterstriche.
    """
    if not title:
        return fallback_id
    # Nur sichere Zeichen behalten
    slug = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    slug = re.sub(r"[\s\-]+", "_", slug).lower()
    return slug or fallback_id
