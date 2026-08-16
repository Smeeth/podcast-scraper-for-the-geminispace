# ADR-0005: 2-Stufen-Feed-Probing, Zero-Media-Storage & Wikipedia-Synthese

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

## Status
Akzeptiert

## Kontext
Die Extraktion von Podcast- und Video-Feeds (insbesondere YouTube-Kanäle und umfangreiche RSS-Feeds) kann ohne vorherige Prüfung zu langen Ladezeiten, unerwünschtem Ressourcenverbrauch und Rate-Limits führen. Zudem besteht das Kernziel des Projekts darin, Metadaten und Transkripte für Wikipedia (MediaWiki-Tabellen und Vorlagen) sowie den Geminispace/Gopherspace aufzubereiten, **ohne** Mediendateien lokal herunterzuladen.

## Entscheidung

1. **2-Stufen-Workflow (Probe ➔ Tiefenscan):**
   - **Stufe 1 (`/api/probe`):** Schnelle Vorab-Prüfung (< 1s) liest ausschließlich Metadaten des Kanal-Headers (Titel, Thumbnail, geschätzte Episodenanzahl) ohne Abruf einzelner Videos/Transkripte.
   - **Stufe 2 (`/api/scrape`):** Der Nutzer bestätigt den Scan und wählt die gewünschte Scrape-Tiefe (25, 50, 100, Alle) sowie den Transkript-Abruf vor Beginn des eigentlichen Scraping-Prozesses.

2. **Zero-Media-Storage-Prinzip:**
   - Mediendateien (Audio/Video in MP3, MP4, WebM etc.) werden **niemals** auf den Server oder das lokale Dateisystem heruntergeladen.
   - Es werden ausschließlich Metadaten, Kapitelmarken, Show-Notes und Transkripte persistiert und direkte Verlinkungen (`audio_or_video_url`) auf die Originalquellen erzeugt.

3. **Wikipedia- & Vorlagen-Synthese:**
   - Unterstützung für standardkonforme MediaWiki-Sortable-Tables (`{| class="wikitable sortable"`) und offizielle Wikipedia-Vorlagen (`{{Episodenliste}}` / `{{Episodentabelle}}`).
   - Automatisches Wiki-Linking von prominenten Gästen und Sachbegriffen (`[[Name]]`) durch den Gemini AI Service.
   - Delta-Export-Modus für inkrementelle Aktualisierungen von Wikipedia-Artikeln.

4. **Transkript-Volltextrecherche & Deep-Linking:**
   - Sekundengenaue Suche über alle gespeicherten Volltext-Transkripte mit direkten Zeitstempel-Sprungmarken zu YouTube (`&t=...s`).

5. **Geminispace Feed-Syndikation (`feed.gmi`):**
   - Erstellung einer subscribable Gemtext-Feed-Datei (`feed.gmi`), die es Gemini-Clients erlaubt, archivierte Kanäle direkt zu abonnieren.

## Konsequenzen
- **Vorteile:** Deutlich reduzierte Latenz, keine Speicherüberlastung, hohe Rechtssicherheit (kein Re-Hosting von Urheberrechtsinhalten), optimale Wikipedia-Workflows und intuitive Benutzeroberfläche.
- **Einschränkungen:** Transkripte hängen von der Verfügbarkeit auf der Quellplattform ab.
