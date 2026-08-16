---
name: validate-gemtext
description: >-
  Use this skill to validate Gemtext (.gmi) files and Gopherspace maps according to gemini
  protocol specifications.
---

# Gemtext & Gopherspace Validator Skill

This skill explains how to validate formatted documents intended for the Geminispace and Gopherspace.

## Execution

Run the Gemtext validation script:

```bash
python .github/scripts/gemtext_validator.py
```

## Gemtext Standard Rules

- Line-length guidelines (avoid extremely long unstructured lines).
- Proper heading formatting (`#`, `##`, `###`).
- Valid link syntax (`=> url [optional label]`).
- Clean list items (`*`).
- Quote formatting (`>`).
