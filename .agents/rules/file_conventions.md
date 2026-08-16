<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Unabbreviated File Extensions (ADR-0004)

This repository strictly enforces complete, standard, and unabbreviated file extensions across all directories.

## Guidelines

1. **YAML Configuration & Workflows**:
   - Always use `.yaml` (e.g. `docker-compose.yaml`, `.github/dependabot.yaml`, `.github/workflows/ci.yaml`).
   - Never use the shortened `.yml` extension.
2. **HTML & Web Assets**:
   - Always use `.html` (never `.htm`).
   - Use standard `.js`, `.json`, and `.css`.
3. **Consistency**:
   - When importing, generating, or refactoring files or CI workflows, verify that no legacy 3-letter abbreviated extensions are introduced.
