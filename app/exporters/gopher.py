# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Gopherspace Exporter (RFC 1436, gophermap).
Generiert standardkonforme Gopher-Menüdateien (gophermaps) für Podcasts und Episoden.
Alle Medien werden direkt als Weblinks (h...\\tURL:...) eingebunden, ohne Mediendateien lokal herunterzuladen.
"""

from typing import List, Optional
from app.models import Podcast, Episode
from app.exporters.utils import safe_slug


def _clean_gopher_field(text: Optional[str]) -> str:
    """
    Bereinigt Text von Tabulatoren und Zeilenumbrüchen (RFC 1436 Konformität).
    Verhindert Spalten-Desynchronisation in Gopher-Clients.
    """
    if not text:
        return ""
    # Tabulatoren durch Leerzeichen ersetzen, Zeilenumbrüche entfernen
    return " ".join(text.replace("\t", " ").split())


def _make_info_line(text: str, host: str = "localhost", port: int = 70) -> str:
    """Erstellt eine RFC-1436 'i' (Informational) Menüzeile."""
    clean = _clean_gopher_field(text)
    return f"i{clean}\t\t{host}\t{port}"


def _make_url_line(display: str, url: str, host: str = "localhost", port: int = 70) -> str:
    """Erstellt eine standardkonforme 'h' (HTML/Weblink) Gophermap-Zeile."""
    clean_disp = _clean_gopher_field(display)
    clean_url = url.strip().replace("\t", "").replace("\n", "").replace("\r", "")
    return f"h{clean_disp}\tURL:{clean_url}\t{host}\t{port}"


def _make_dir_line(display: str, selector: str, host: str = "localhost", port: int = 70) -> str:
    """Erstellt eine '1' (Subdirectory / Submenu) Gophermap-Zeile."""
    clean_disp = _clean_gopher_field(display)
    clean_sel = selector.strip().replace("\t", "")
    return f"1{clean_disp}\t{clean_sel}\t{host}\t{port}"


def generate_gophermap_podcast(podcast: Podcast, host: str = "localhost", port: int = 70) -> str:
    """
    Erstellt ein RFC-1436 konformes gophermap-Dokument für einen Podcast.
    """
    lines: List[str] = [
        _make_info_line(f"============================================================", host, port),
        _make_info_line(f" Podcast: {podcast.title}", host, port),
        _make_info_line(f" Autor:   {podcast.author or 'Unbekannt'}", host, port),
        _make_info_line(f" Format:  {podcast.platform.upper()}", host, port),
        _make_info_line(f"============================================================", host, port),
        _make_info_line("", host, port),
    ]

    if podcast.url:
        lines.append(_make_url_line(f"[Web] Offizielle Seite ({podcast.title})", podcast.url, host, port))
    if podcast.feed_url and podcast.feed_url != podcast.url:
        lines.append(_make_url_line("[RSS] Quell-Feed", podcast.feed_url, host, port))

    lines.append(_make_info_line("", host, port))

    if podcast.description:
        lines.append(_make_info_line("--- Beschreibung ---", host, port))
        # Beschreibung in Zeilen zerlegen
        for line in podcast.description.strip().split("\n"):
            clean = _clean_gopher_field(line)
            if clean:
                # Lange Zeilen bei ~70 Zeichen umbrechen für schmale Gopher-Terminals
                while len(clean) > 75:
                    split_idx = clean[:75].rfind(" ")
                    if split_idx == -1:
                        split_idx = 75
                    lines.append(_make_info_line(clean[:split_idx], host, port))
                    clean = clean[split_idx:].strip()
                if clean:
                    lines.append(_make_info_line(clean, host, port))
        lines.append(_make_info_line("", host, port))

    lines.append(_make_info_line(f"--- Episodenliste ({len(podcast.episodes)} Folgen) ---", host, port))
    lines.append(_make_info_line("", host, port))

    for ep in podcast.episodes:
        ep_num = f"#{ep.episode_number} " if ep.episode_number else ""
        date_str = f" [{ep.published_at.strftime('%Y-%m-%d')}]" if ep.published_at else ""
        dur_str = f" ({ep.duration_seconds // 60}m)" if ep.duration_seconds else ""

        title_line = f"{ep_num}{ep.title}{date_str}{dur_str}"
        lines.append(_make_info_line(title_line, host, port))

        if ep.audio_or_video_url:
            lines.append(_make_url_line(f"  -> Audio/Video: {ep.title}", ep.audio_or_video_url, host, port))

        if ep.chapters and len(ep.chapters) > 0:
            for ch in ep.chapters:
                time_str = ch.get("start_time_formatted") or f"{int(ch.get('start_time', 0))}s"
                ch_title = ch.get("title", "Kapitel")
                lines.append(_make_info_line(f"     [{time_str}] {ch_title}", host, port))

        lines.append(_make_info_line("", host, port))

    lines.append(_make_info_line("------------------------------------------------------------", host, port))
    lines.append(_make_dir_line("<- Zurueck zur Hauptuebersicht", "/", host, port))
    lines.append(_make_info_line("Generiert mit Podcast & Media Channel Researcher (GPL-3.0)", host, port))

    return "\n".join(lines) + "\n"


def generate_gophermap_index(podcasts: List[Podcast], host: str = "localhost", port: int = 70) -> str:
    """
    Erstellt die Haupt-gophermap für den Gopherspace Root-Directory.
    """
    lines: List[str] = [
        _make_info_line("============================================================", host, port),
        _make_info_line("   Podcast & Media Channel Researcher Archive (Gopherspace) ", host, port),
        _make_info_line("============================================================", host, port),
        _make_info_line("Willkommen im dezentralen Medien-Archiv.", host, port),
        _make_info_line("Saeckliche Folgen sind als direkte Web-Links hinterlegt.", host, port),
        _make_info_line("", host, port),
        _make_info_line(f"--- Archivierte Medienkanale ({len(podcasts)}) ---", host, port),
        _make_info_line("", host, port),
    ]

    if not podcasts:
        lines.append(_make_info_line("Noch keine Podcasts erfasst.", host, port))
    else:
        for p in podcasts:
            slug = safe_slug(p.title, p.id)
            ep_count = len(p.episodes) if p.episodes else 0
            author_str = f" ({p.author})" if p.author else ""
            display_title = f"{p.title}{author_str} [{ep_count} Folgen]"

            # Verzeichnis-Link auf Podcast-Unterordner
            lines.append(_make_dir_line(display_title, f"/{slug}", host, port))
            if p.description:
                short_desc = _clean_gopher_field(p.description)[:70]
                lines.append(_make_info_line(f"  {short_desc}...", host, port))
            lines.append(_make_info_line("", host, port))

    lines.append(_make_info_line("------------------------------------------------------------", host, port))
    lines.append(_make_info_line("Server: Podcast & Media Researcher Engine (GPL-3.0)", host, port))

    return "\n".join(lines) + "\n"
