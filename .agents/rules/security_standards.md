<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Security Standards (ADR-0001)

All changes and additions must comply with the Security First architecture defined in ADR-0001.

## Rules

1. **SSRF Validation & URL Reconstruction (Taint Barrier)**:
   - Always run `validate_and_reconstruct_safe_url(url)` (or `is_safe_external_url(url)`) before fetching any external resource via HTTP/HTTPS or initiating `yt-dlp`.
   - Pass the reconstructed URL string strictly reassembled from validated components (`scheme`, `netloc`, `path`, `query`) to HTTP clients to maintain the CodeQL taint barrier.
   - Never allow local network requests (RFC 1918), loopback, link-local, cloud metadata (`169.254.169.254`, `metadata.google.internal`), or non-http/https protocols.

2. **XML & RSS Feed Parsing**:
   - Use `defusedxml` (`defusedxml.ElementTree` or `defusedxml.minidom`).
   - Never use the standard library `xml.etree.ElementTree` directly on untrusted inputs.

3. **Zero Secrets & GitHub Security API**:
   - Never commit tokens, credentials, or `.env` files.
   - Access configuration values through `app.config.get_settings()`.
   - The `.env` `GITHUB_TOKEN` is used for automated security monitoring (CodeQL, Dependabot, Secret Scanning) via the `github-security` skill.

4. **Content Security Policy (CSP)**:
   - Do not add remote CDN `<script>` or `<link>` tags. All assets must be bundled locally in `app/static/vendor/`.

## Validation

Always verify using:

```bash
python .github/scripts/security_audit.py
python .github/scripts/check_github_security.py
```

