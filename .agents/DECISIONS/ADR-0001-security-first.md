# ADR-0001: Security > Performance > Usability als Leitprinzip

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

## Status
Akzeptiert

## Kontext
Die Web-Applikation verarbeitet externe, unkontrollierte Datenquellen aus dem Internet (RSS-Feeds, XML-Dokumente, Video-URLs, externe API-Endpunkte und Benutzereingaben). Dies birgt erhebliche Risiken für SSRF (Server-Side Request Forgery), XXE (XML External Entity Attacks), Denial of Service (XML-Bomben), Command Injection, SQL Injection und Token-Exposition.

## Entscheidung
Jede Architektur- und Codeentscheidung folgt zwingend der Priorität **Security > Performance > Usability**. 

Konkret gelten folgende Regeln:

1. **Zero-Trust Input-Validierung & SSRF-Schutz:**
   - Alle URLs müssen vor dem HTTP-Zugriff validiert werden.
   - Private IP-Bereiche (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Loopback (`127.0.0.0/8`), Link-Local (`169.254.0.0/16`), IPv6-Local/Loopback sowie Cloud-Metadaten-IPs (`169.254.169.254`) werden strikt geblockt.
   - Es sind ausschließlich `http` und `https` Schemas zulässig (kein `file://`, `gopher://`, `ftp://`).

2. **Sichere XML/RSS-Verarbeitung (`defusedxml`):**
   - Standard-XML-Parser in Python sind anfällig für XXE und Entitäten-Expansion.
   - Sämtliche XML-Verarbeitungen (RSS, Atom, Apple Podcast Namespaces) müssen über `defusedxml` gehärtet werden.

3. **Keine Shell-Ausführungen / Command Injection Schutz:**
   - `yt-dlp` wird ausschließlich über seine Python-interne API instanziiert (`YoutubeDL({...})`).
   - Keine Verwendung von `os.system()`, `subprocess.Popen(..., shell=True)` für Scraper.

4. **Secrets- & Key-Management:**
   - Gemini API-Keys und Datenbankpasswörter dürfen weder in Client-Responses, noch in Logging-Ausgaben oder Fehlermeldungen auftauchen.
   - Verwendung von `SecretStr` / Pydantic Masking.

5. **Container-Härtung:**
   - Dockerfile basiert auf unprivilegiertem Non-Root-User (`appuser`, UID 10001).
   - Minimales Base-Image (`python:3.11-slim`), keine Build-Tools im finalen Image.

6. **Content Security Policy (CSP) & Header:**
   - Keine externen CDNs zur Laufzeit; alle CSS/JS-Assets (Bootstrap 5) sind lokal gebündelt.
   - Strikte CSP: `default-src 'self'`.

## Konsequenzen
- **Vorteile:** Höchster Schutz gegen Server-Kompromittierung, Datenabfluss und Denial of Service.
- **Trade-offs:** Leicht erhöhter Validierungs-Overhead bei Feed-Abrufen und striktere Beschränkungen für vom Benutzer eingegebene URLs.
