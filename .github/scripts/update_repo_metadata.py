#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
"""
Automatisches Skript zum Aktualisieren der GitHub-Repository-Metadaten
(Description & Topics) über die GitHub REST API oder GitHub CLI.
"""

import os
import sys
import json
import urllib.request
import urllib.error

REPO_OWNER = "Smeeth"
REPO_NAME = "podcast-scraper-for-the-geminispace"

DESCRIPTION = (
    "Security-hardened podcast & media researcher for YouTube, RSS & Apple Podcasts. "
    "Features Google Gemini AI analysis, automated Wikipedia Wikitext table generation, "
    "SSRF defense, and native Gemtext (.gmi) & Gophermap archive publishing for Geminispace "
    "and Gopherspace. Built with FastAPI, async PostgreSQL & Bootstrap 5 Dark Mode under GNU GPL-3.0."
)

TOPICS = [
    "podcast",
    "geminispace",
    "gopherspace",
    "gemini-protocol",
    "gemtext",
    "podcast-scraper",
    "rss-parser",
    "youtube-scraper",
    "google-gemini",
    "ai-analysis",
    "wikipedia-tables",
    "wikitext",
    "fastapi",
    "sqlalchemy-async",
    "postgresql",
    "bootstrap5",
    "dark-mode",
    "ssrf-protection",
    "defusedxml",
    "gplv3"
]


def update_via_api(token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Podcast-Scraper-Metadata-Updater"
    }

    # 1. Update Description
    repo_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    repo_data = json.dumps({"description": DESCRIPTION}).encode("utf-8")
    req = urllib.request.Request(repo_url, data=repo_data, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            print("[ERFOLG] Repository Description erfolgreich aktualisiert.")
    except urllib.error.HTTPError as e:
        print(f"[FEHLER] Description konnte nicht gesetzt werden: HTTP {e.code} ({e.reason})")

    # 2. Update Topics
    topics_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/topics"
    topics_data = json.dumps({"names": TOPICS}).encode("utf-8")
    req = urllib.request.Request(topics_url, data=topics_data, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[ERFOLG] {len(TOPICS)} Topics erfolgreich gesetzt!")
    except urllib.error.HTTPError as e:
        print(f"[FEHLER] Topics konnten nicht gesetzt werden: HTTP {e.code} ({e.reason})")


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]

    if not token:
        print("\n[INFO] Für die automatische Aktualisierung wird ein GitHub Token benötigt.")
        print("Führe das Skript aus mit:")
        print("  python .github/scripts/update_repo_metadata.py <DEIN_GITHUB_TOKEN>")
        print("Oder setze die Umgebungsvariable $env:GITHUB_TOKEN = '<TOKEN>'")
        sys.exit(1)

    update_via_api(token)


if __name__ == "__main__":
    main()
