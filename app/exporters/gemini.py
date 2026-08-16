# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Geminispace Exporter (MIME-Type: text/gemini, .gmi).
Generiert standardkonforme Gemtext-Dokumente für Podcasts und Episoden.
Alle Medien werden direkt verlinkt (=> URL), ohne Mediendateien lokal herunterzuladen.
"""

from collections.abc import Sequence

from app.exporters.utils import safe_slug
from app.models import Podcast


def _clean_gemtext_line(text: str | None) -> str:
    """Bereinigt Textzeilen von Zeilenumbrüchen für sichere Gemtext-Titel und -Links."""
    if not text:
        return ""
    return " ".join(text.split())


def generate_gemtext_podcast(podcast: Podcast) -> str:
    """
    Erstellt ein vollständiges Gemtext (.gmi) Dokument für einen einzelnen Podcast
    inklusive Metadaten, Episodenliste, Shownotes, Kapitelmarken und direkten Medien-Links.
    """
    lines: list[str] = [
        f"# 📻 {_clean_gemtext_line(podcast.title)}",
        f"Autor / Kanal: {_clean_gemtext_line(podcast.author or 'Unbekannt')}",
        f"Plattform: {podcast.platform.upper()}",
    ]

    if podcast.url:
        lines.append(f"=> {podcast.url} 🔗 Offizielle Webpräsenz / Original-Kanal")
    if podcast.feed_url and podcast.feed_url != podcast.url:
        lines.append(f"=> {podcast.feed_url} 📡 RSS-Feed / Quell-Feed")

    lines.append("")

    if podcast.description:
        lines.append("## 📝 Beschreibung")
        for para in podcast.description.strip().split("\n\n"):
            clean_p = _clean_gemtext_line(para)
            if clean_p:
                lines.append(clean_p)
        lines.append("")

    episodes = podcast.episodes or []
    lines.append(f"## 📋 Episoden ({len(episodes)} Folgen)")
    lines.append("")

    for ep in episodes:
        ep_num_str = f"#{ep.episode_number} " if ep.episode_number else ""
        lines.append(f"### {ep_num_str}{_clean_gemtext_line(ep.title)}")

        # Metadaten-Zeile
        meta_parts = []
        if ep.published_at:
            meta_parts.append(f"Datum: {ep.published_at.strftime('%Y-%m-%d')}")
        if ep.duration_seconds:
            mins = ep.duration_seconds // 60
            meta_parts.append(f"Dauer: {mins} Min.")
        if meta_parts:
            lines.append(f"> {' | '.join(meta_parts)}")

        # Direkter Medien-Link (Audio / Video URL)
        if ep.audio_or_video_url:
            lines.append(f"=> {ep.audio_or_video_url} ▶️ Folge anhören / ansehen ({ep_num_str.strip() or 'Direktlink'})")

        # Kapitelmarken
        if ep.chapters and isinstance(ep.chapters, list) and len(ep.chapters) > 0:
            lines.append("")
            lines.append("Kapitelmarken:")
            for ch in ep.chapters:
                if isinstance(ch, dict):
                    time_str = ch.get("start_time_formatted") or f"{int(ch.get('start_time', 0))}s"
                    ch_title = _clean_gemtext_line(ch.get("title", "Kapitel"))
                    lines.append(f"* [{time_str}] {ch_title}")

        # Show Notes Zusammenfassung
        if ep.description:
            clean_desc = _clean_gemtext_line(ep.description)[:400]
            if clean_desc:
                lines.append("")
                lines.append(f"{clean_desc}...")

        lines.append("")

    lines.append("---")
    lines.append("=> index.gmi ⬅️ Zurück zur Podcast-Übersicht")
    lines.append("Generiert mit Podcast & Media Channel Researcher (GPL-3.0)")

    return "\n".join(lines) + "\n"


def generate_gemtext_index(podcasts: Sequence[Podcast]) -> str:
    """
    Erstellt die Haupt-Indexdatei (index.gmi) für den Geminispace
    mit einer Übersicht aller archivierten Podcasts und Kanäle.
    """
    lines: list[str] = [
        "# 📻 Podcast & Media Channel Archive (Geminispace)",
        "Willkommen im dezentralen Podcast- und Medienarchiv für den Geminispace.",
        "Sämtliche Episoden sind als direkte Medien-Links referenziert.",
        "",
        f"## 📚 Verfügbare Medienkanäle ({len(podcasts)})",
        "",
    ]

    if not podcasts:
        lines.append("Aktuell sind noch keine Podcasts im Archiv erfasst.")
    else:
        for p in podcasts:
            slug = safe_slug(p.title, p.id)
            ep_count = len(p.episodes) if p.episodes else 0
            author_str = f" von {_clean_gemtext_line(p.author)}" if p.author else ""
            lines.append(f"=> {slug}.gmi 🎙️ {_clean_gemtext_line(p.title)} ({ep_count} Folgen{author_str})")
            if p.description:
                short_desc = _clean_gemtext_line(p.description)[:160]
                lines.append(f"> {short_desc}...")
            lines.append("")

    lines.append("---")
    lines.append("Server-Info: Generiert mit Podcast & Media Channel Researcher & AI Analyzer (GPL-3.0)")
    return "\n".join(lines) + "\n"
