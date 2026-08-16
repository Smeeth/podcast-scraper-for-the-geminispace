---
name: verify-spdx
description: >-
  Use this skill to check and verify that all source code, script, and configuration files
  contain the required GPL-3.0 SPDX license header.
---

# Verify SPDX Headers Skill

This skill explains how to validate license compliance across the repository.

## Execution

Run the automated SPDX verification script:

```bash
python .github/scripts/verify_spdx_headers.py
```

## Expected Result

- **Success (`exit 0`)**: `[ERFOLG] Alle Quelldateien besitzen einen gültigen SPDX-GPL-3.0-Header.`
- **Failure (`exit 1`)**: Lists all files missing the required header.

## Fixing Missing Headers

Add the appropriate SPDX header to the top of any flagged file:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
```
