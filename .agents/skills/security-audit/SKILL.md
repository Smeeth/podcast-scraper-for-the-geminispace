---
name: security-audit
description: >-
  Use this skill to perform a security audit on the codebase, verifying SSRF protections,
  XML parser safety, and secret prevention.
---

# Security Audit Skill

This skill explains how to run the automated security validation suite based on ADR-0001.

## Execution

Run the security audit script:

```bash
python .github/scripts/security_audit.py
```

## Checks Performed

1. **SSRF Filtering**: Ensures all external network fetches pass through `is_safe_external_url`.
2. **DefusedXML**: Verifies that standard `xml.etree` is not used directly without protection.
3. **Secret Scanning**: Scans for embedded keys, passwords, and tokens.
4. **Dependency Safety**: Checks dependencies in `requirements.txt` for known vulnerabilities.
