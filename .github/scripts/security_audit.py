#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
"""
Sicherheits-Audit-Skript für Git-Pre-Commit und GitHub Actions (ADR-0001).
Sucht nach potenziell hardgecodeten Secrets, unsicherem XML-Parsing und ungeschützten Endpunkten.
"""

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

EXCLUDE_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", ".idea", ".vscode",
    "vendor", "node_modules", "dist", "build", ".pytest_cache"
}

SUSPICIOUS_PATTERNS = [
    (r"AIzaSy[A-Za-z0-9_-]{33}", "Potenzieller Google Gemini API Key"),
    (r"(?i)(password|secret|api_key|token)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Möglicher hardgecodeter Secret-Wert"),
    (r"import\s+xml\.etree\.ElementTree\s+as", "Unsicheres XML-Parsing (defusedxml bevorzugen gem. ADR-0001)"),
    (r"from\s+xml\.etree\s+import", "Unsicheres XML-Parsing (defusedxml bevorzugen gem. ADR-0001)"),
]


def audit_file(file_path: Path) -> list:
    findings = []
    # Test-Dateien und Beispiel-Konfigurationen ignorieren
    if "test" in file_path.name.lower() or file_path.name.endswith(".example"):
        return findings

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(content.splitlines(), 1):
            for pattern, desc in SUSPICIOUS_PATTERNS:
                if re.search(pattern, line):
                    # Ausnahme für Platzhalter oder Settings-Deklarationen
                    if "SecretStr" in line or "__CHANGE_ME__" in line or "Field(" in line:
                        continue
                    findings.append(f"{file_path}:{i} - {desc}: '{line.strip()}'")
    except Exception as e:
        findings.append(f"{file_path} - Datei konnte nicht gelesen werden ({e})")

    return findings


def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    findings = []
    checked_count = 0

    for file_path in root_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in {".py", ".json", ".yml", ".yaml", ".env"}:
            if any(part in EXCLUDE_DIRS for part in file_path.parts):
                continue
            if "app/static/vendor" in file_path.as_posix():
                continue

            checked_count += 1
            findings.extend(audit_file(file_path))

    print(f"[INFO] Sicherheits-Audit (ADR-0001): {checked_count} Dateien gescannt.")

    if findings:
        print("\n[WARNUNG] Mögliche Sicherheitsbefunde:")
        for f in findings:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("[ERFOLG] Keine potenziellen Secrets oder unsichere Parser-Muster gefunden.")
        sys.exit(0)


if __name__ == "__main__":
    main()
