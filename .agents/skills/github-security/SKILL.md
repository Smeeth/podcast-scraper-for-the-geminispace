---
name: github-security
description: >-
  Use this skill to inspect, audit, and triage GitHub Security alerts (CodeQL,
  Dependabot, Secret Scanning) using the GITHUB_TOKEN configured in .env.
---

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# GitHub Security Audit & Triage Skill

This skill documents how agents and developers can directly query and triage GitHub security reports for the repository using the API token stored in `.env`.

---

## 1. Authentication & Environment

The local `.env` file contains the `GITHUB_TOKEN` (Fine-Grained Personal Access Token with Security Events and Code Scanning read/write permissions).

Agents must **never** hardcode, echo, or commit this token (ADR-0001). Always load it dynamically via `pydantic-settings`, `python-dotenv`, or `os.getenv("GITHUB_TOKEN")`.

---

## 2. Automated Security Audit Script

Execute the built-in audit script to scan all open alerts across CodeQL, Dependabot, and Secret Scanning:

```bash
python .github/scripts/check_github_security.py
```

---

## 3. GitHub Security Endpoints & Categories

| Security Category | GitHub REST API Endpoint | Purpose |
| :--- | :--- | :--- |
| **Code Scanning (CodeQL)** | `GET /repos/{owner}/{repo}/code-scanning/alerts?state=open` | SAST code vulnerabilities (SSRF, CWE-117, CWE-611) |
| **Dependabot** | `GET /repos/{owner}/{repo}/dependabot/alerts?state=open` | Known CVEs in Python/Actions dependencies |
| **Secret Scanning** | `GET /repos/{owner}/{repo}/secret-scanning/alerts?state=open` | Leaked API keys or credentials |

---

## 4. Triage & Remediation Workflow

1. **Verify Alert**: Inspect the affected file and line location reported in the alert.
2. **Implement Fix**: Apply architectural defense-in-depth:
   - For SSRF: Reconstruct URLs via `validate_and_reconstruct_safe_url()` and check against IP blocklists.
   - For Log Injection: Sanitize inputs with `sanitize_log_message()`.
   - For XML safety: Ensure `defusedxml` is enforced.
3. **Verify Locally**: Run test suite, Bandit, Pyright, and Ruff.
4. **Push & Validate**: Push changes to GitHub and verify that the automated CodeQL / CI workflow completes green.
