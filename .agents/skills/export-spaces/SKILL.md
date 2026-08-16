---
name: export-spaces
description: >-
  Use this skill when generating, updating, or publishing research reports and podcast
  summaries to Geminispace (.gmi) or Gopherspace (gophermap).
---

# Geminispace & Gopherspace Exporter Skill

This skill explains how the project exports data to alternative internet protocols.

## Components

- **Gemini Exporter**: `app/exporters/gemini.py`
  Generates clean Gemtext (`.gmi`) files in `public/gemini/`.
- **Gopher Exporter**: `app/exporters/gopher.py`
  Generates `gophermap` structures in `public/gopher/`.

## Directory Targets

- `public/gemini/index.gmi`: Main landing page for Geminispace capsules.
- `public/gopher/gophermap`: Root index map for Gopher servers.

## Publication Rules

1. Never commit dynamically generated ephemeral `.gmi` or `gophermap` subfiles unless explicitly updating the static index template.
2. Verify all generated `.gmi` files with `.github/scripts/gemtext_validator.py`.
