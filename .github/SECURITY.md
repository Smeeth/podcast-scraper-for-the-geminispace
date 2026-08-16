<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Security Policy

The **Podcast & Media Channel Researcher** team takes the security of our application, dependencies, and user data seriously. We adhere to a **Security First** principle ([ADR-0001](file:///.agents/DECISIONS/ADR-0001-security-first.md)) where security considerations take precedence over performance and usability.

---

## Supported Versions

Only the latest release and the current `main` branch receive active security updates and vulnerability patches.

| Version / Branch | Supported          | Notes                                |
| ---------------- | ------------------ | ------------------------------------ |
| `main`           | :white_check_mark: | Active development branch            |
| Latest Release   | :white_check_mark: | Production-ready tags                |
| `< Latest`       | :x:                | Please upgrade to the latest release |

---

## Reporting a Vulnerability

We strongly encourage coordinated, responsible disclosure. **Please do NOT report security vulnerabilities through public GitHub Issues, Pull Requests, or Discussions.**

### Preferred Method: GitHub Private Vulnerability Reporting

1. Navigate to the **Security** tab of this repository.
2. Click on **Advisories** and select **Report a vulnerability**.
3. Fill out the report form with detailed reproduction steps, proof of concept, and impact assessment.
4. Submit the report. It will only be visible to repository maintainers.

### Alternative Contact

If GitHub Private Vulnerability Reporting is unavailable, please reach out privately via the maintainer contact channels specified in the project repository metadata.

---

## What to Include in Your Report

To help us investigate and resolve the issue quickly, please include:

- **Vulnerability Type:** (e.g., SSRF, XXE, Command Injection, Insecure Deserialization, Secret Exposure).
- **Affected Component:** Specific file, endpoint, or scraper adapter (e.g., `app/scrapers/`, `app/config.py`, FastAPI routers).
- **Step-by-step Reproduction:** Clear instructions or a minimal proof-of-concept (PoC) payload.
- **Impact Assessment:** How an attacker could exploit the vulnerability and potential blast radius.
- **Suggested Fix:** (Optional) Any recommended patches or mitigations.

---

## Response & Disclosure Process

1. **Acknowledgment:** We will acknowledge receipt of your vulnerability report within **48 hours**.
2. **Triage & Verification:** Maintainers will validate the findings and assess the severity using CVSS scoring.
3. **Remediation:** A patch will be developed and tested in a private security advisory branch.
4. **Coordinated Release:** Once the patch is verified, a new release will be tagged and a security advisory will be published.
5. **Credit:** With your permission, we will acknowledge your contribution in the security advisory release notes.

---

## Core Security Safeguards in This Project

For reference, this project implements the following architectural security measures:

- **SSRF Defense:** Strict validation and URL reconstruction (`app.config.validate_and_reconstruct_safe_url`) blocking private IPs (RFC 1918), loopback, link-local, and cloud metadata endpoints.
- **XML/Feed Hardening:** Feed parsing uses `defusedxml` to mitigate Billion Laughs and XXE attacks.
- **Injection Protection:** Direct shell invocations are prohibited; media extraction (`yt-dlp`) runs via internal Python APIs without shell execution.
- **Zero Secrets Policy:** API keys and sensitive tokens are masked and loaded strictly from environment variables via Pydantic `SecretStr`.
- **Container Hardening:** Docker runtime operates as an unprivileged, non-root user (`appuser`, UID 10001).
- **No External CDNs:** Strict Content Security Policy (`default-src 'self'`) with all frontend assets bundled locally.
