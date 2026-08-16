<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Agent Guidelines: Podcast & Media Channel Researcher

This document provides root operating guidelines for AI coding agents and autonomous pair-programming tools operating in this repository.

For German project documentation and setup notes, see [GEMINI.md](file:///GEMINI.md).

---

## 1. Living Agent Documentation Structure (`.agents/`)

Autonomous agents must orient themselves using the following dedicated documentation and rule hierarchy in `.agents/`:

- **System Architecture**: [.agents/ARCHITECTURE.md](file:///.agents/ARCHITECTURE.md) (4-layer modular system, data flows, components)
- **Project Context & Roadmap**: [.agents/CONTEXT.md](file:///.agents/CONTEXT.md) (Development status, milestones, environment notes)
- **Architectural Decision Records (`.agents/DECISIONS/`)**:
  - [ADR-0001](file:///.agents/DECISIONS/ADR-0001-security-first.md): Security First Principle (Zero Secrets, SSRF Validation, `defusedxml`, CSP)
  - [ADR-0002](file:///.agents/DECISIONS/ADR-0002-modular-scraper-adapter.md): Modular Scraper Adapter Pattern (`BaseScraper`, `ScraperFactory`)
  - [ADR-0003](file:///.agents/DECISIONS/ADR-0003-single-file-commits.md): Granular Single-File Commits in English
  - [ADR-0004](file:///.agents/DECISIONS/ADR-0004-unabbreviated-file-extensions.md): Explicit Unabbreviated File Extensions (`.yaml` instead of `.yml`)
- **Agent Rules (`.agents/rules/`)**:
  - [commit_policy.md](file:///.agents/rules/commit_policy.md): Conventional Commits & single-file commit workflow
  - [file_conventions.md](file:///.agents/rules/file_conventions.md): Enforcement of full, unabbreviated file extensions
  - [python_backend.md](file:///.agents/rules/python_backend.md): Async Python 3.11, FastAPI, SQLAlchemy 2.0 async coding standards
  - [security_standards.md](file:///.agents/rules/security_standards.md): Mandatory URL validation, XML safety, and key masking
  - [spdx_license.md](file:///.agents/rules/spdx_license.md): GPL-3.0 SPDX header rules
- **Specialized Skills (`.agents/skills/`)**:
  - `export-spaces`: Publishing reports to Geminispace (`.gmi`) and Gopherspace (`gophermap`)
  - `run-tests`: Running test suite and troubleshooting test failures
  - `security-audit`: Scanning for SSRF vulnerabilities, raw XML parsers, and leaked secrets
  - `validate-gemtext`: Validating Gemtext protocol syntax and Gophermaps
  - `verify-spdx`: Validating SPDX license headers across all source files

---

## 2. Core Operating Principles

1. **GPL-3.0 SPDX License**: Every source, script, or configuration file must include the SPDX identifier:
   `SPDX-License-Identifier: GPL-3.0-or-later`
2. **Security First (ADR-0001)**:
   - Validate external URLs with `app.config.is_safe_external_url` prior to making network requests.
   - Parse XML feeds exclusively with `defusedxml`.
   - Never commit `.env` or plain-text secrets.
   - Bundle all frontend dependencies locally (no external CDNs).
3. **Async Architecture & Scraper Modularity (ADR-0002)**:
   - Use Python 3.11 `asyncio`, FastAPI async handlers, and SQLAlchemy 2.0 async sessions.
   - Implement new scrapers as adapters extending `BaseScraper` and registered in `ScraperFactory`.
4. **Single-File Commits (ADR-0003)**:
   - Commit changes per file with concise Conventional Commit messages in English.
5. **Explicit File Extensions (ADR-0004)**:
   - Always use full, standard extensions (`.yaml`, `.html`, `.md`, `.js`, `.json`). Never use `.yml` or `.htm`.
6. **Clean Diagnostics & Scout Rule (`@current_problems`)**:
   - Ensure zero compiler, linter, or markdownlint warnings on all newly created or modified files.
   - Leave modified files cleaner than you found them without scope creep into untouched legacy modules.
7. **Quality Gate Verification**:
   - Run verification scripts and test suite before finalizing changes:
     - `python .github/scripts/verify_spdx_headers.py`
     - `python .github/scripts/security_audit.py`
     - `python .github/scripts/gemtext_validator.py`
     - `pytest tests -v`
