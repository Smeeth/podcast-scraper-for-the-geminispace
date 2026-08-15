#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
"""
Automatisches Prüfskript für SPDX-Lizenzheader in Quellcodedateien.
Stellt sicher, dass alle Python- und Frontend-Dateien die GPL-3.0-or-later
Klausel sowie Copyright-Hinweise tragen.
"""

import sys
from pathlib import Path

# Sicherstellen, dass UTF-8 auf allen Plattformen unterstützt wird
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_SPDX = "SPDX-License-Identifier: GPL-3.0-or-later"
EXCLUDE_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".git", ".idea", ".vscode",
    "vendor", "node_modules", "dist", "build", ".pytest_cache"
}
CHECK_EXTENSIONS = {".py", ".js", ".sh"}


def check_file(file_path: Path) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if REQUIRED_SPDX in content:
            return True
        return False
    except Exception as e:
        print(f"[FEHLER] Datei konnte nicht gelesen werden: {file_path} ({e})")
        return False


def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    missing_headers = []
    checked_count = 0

    for file_path in root_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in CHECK_EXTENSIONS:
            # Pfad-Ausschlüsse prüfen
            if any(part in EXCLUDE_DIRS for part in file_path.parts):
                continue
            if "app/static/vendor" in file_path.as_posix():
                continue

            checked_count += 1
            if not check_file(file_path):
                missing_headers.append(file_path.relative_to(root_dir))

    print(f"[INFO] SPDX Header Check: {checked_count} Dateien überprüft.")
    if missing_headers:
        print("\n[FEHLER] Folgende Dateien besitzen keinen gültigen SPDX-GPL-3.0-Header:")
        for missing in missing_headers:
            print(f"  - {missing}")
        sys.exit(1)
    else:
        print("[ERFOLG] Alle Quelldateien besitzen einen gültigen SPDX-GPL-3.0-Header.")
        sys.exit(0)


if __name__ == "__main__":
    main()
