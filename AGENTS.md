<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Agent Guidelines: Podcast & Media Channel Researcher

This file provides root operating guidelines for AI coding agents and autonomous pair-programming tools in this repository.

For full architectural context and German project notes, see [GEMINI.md](file:///GEMINI.md) and [.agents/ARCHITECTURE.md](file:///.agents/ARCHITECTURE.md).

## Core Principles

1. **GPL-3.0 SPDX License**: Every file must start with SPDX license identifier (`SPDX-License-Identifier: GPL-3.0-or-later`) and copyright notice.
2. **Security First (ADR-0001)**:
   - Validate external URLs with `app.config.is_safe_external_url` before fetching.
   - Use `defusedxml` for all XML parsing.
   - Never commit `.env` or credentials.
   - No external CDNs (strict CSP compliance).
3. **Async Architecture**: Use Python 3.11 `asyncio`, FastAPI async route handlers, and SQLAlchemy 2.0 async sessions.
4. **Single-File Commits (ADR-0003)**: Commit individual files with clear Conventional Commit messages in English.
5. **Quality Gate**: Always run `pytest tests -v` and `python .github/scripts/verify_spdx_headers.py` before finalizing changes.
