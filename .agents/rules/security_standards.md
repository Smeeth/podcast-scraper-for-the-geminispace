<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Security Standards (ADR-0001)

All changes and additions must comply with the Security First architecture defined in ADR-0001.

## Rules

1. **SSRF Validation**:
   - Always run `is_safe_external_url(url)` before fetching any external resource via HTTP/HTTPS or initiating `yt-dlp`.
   - Never allow local network requests (RFC 1918), loopback, link-local, or non-http/https protocols.

2. **XML & RSS Feed Parsing**:
   - Use `defusedxml` (`defusedxml.ElementTree` or `defusedxml.minidom`).
   - Never use the standard library `xml.etree.ElementTree` directly on untrusted inputs.

3. **Zero Secrets**:
   - Never commit tokens, credentials, or `.env` files.
   - Access configuration values through `app.config.get_settings()`.

4. **Content Security Policy (CSP)**:
   - Do not add remote CDN `<script>` or `<link>` tags. All assets must be bundled locally in `app/static/vendor/`.

## Validation

Always verify using:

```bash
python .github/scripts/security_audit.py
```
