<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Single-File Commit Policy (ADR-0003)

This repository follows a strict granular single-file commit strategy.

## Guidelines

1. **One File Per Commit**: Each newly added or modified file should be committed in a separate, isolated git commit.
2. **Language**: Commit messages must be written in **English**.
3. **Format**: Follow the Conventional Commits format:
   - `feat(<scope>): <description>`
   - `fix(<scope>): <description>`
   - `refactor(<scope>): <description>`
   - `test(<scope>): <description>`
   - `docs(<scope>): <description>`
   - `chore(<scope>): <description>`
4. **Examples**:
   - `docs(agents): add python backend coding rule`
   - `chore(vscode): configure debug launch targets`
   - `feat(exporter): add gemtext metadata header generator`
