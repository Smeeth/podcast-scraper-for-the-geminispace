#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors
"""
Validator für Gemtext- (.gmi) und Gophermap-Dateien.
Prüft auf Konformität mit den Geminispace- und Gopherspace-Standards.
"""

import sys
from pathlib import Path
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def validate_gemtext(content: str, filename: str) -> list:
    """Validiert eine Gemtext-Datei (text/gemini)."""
    errors = []
    lines = content.splitlines()
    in_preformatted = False

    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            in_preformatted = not in_preformatted
            continue

        if in_preformatted:
            continue

        # Link-Zeilen-Formatierung: =>[whitespace]URL[whitespace][label]
        if line.startswith("=>"):
            match = re.match(r"^=>\s*(\S+)(?:\s+(.*))?$", line)
            if not match:
                errors.append(f"{filename}:{i} - Ungültige Gemtext-Linkzeile: '{line}'")
            else:
                url = match.group(1)
                if "\t" in line:
                    errors.append(f"{filename}:{i} - Tabulatoren in Gemtext-Links vermeiden.")

        # Überschriften-Checks
        if line.startswith("#"):
            if not re.match(r"^#{1,3}\s+\S+", line):
                errors.append(f"{filename}:{i} - Ungültige Überschrift (Leerzeichen nach # erforderlich): '{line}'")

    if in_preformatted:
        errors.append(f"{filename} - Nicht geschlossener Preformatted-Block (```) am Dateiende.")

    return errors


def validate_gophermap(content: str, filename: str) -> list:
    """Validiert eine Gophermap nach RFC 1436."""
    errors = []
    lines = content.splitlines()

    valid_types = {
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "g", "I", "h", "i", "s", "d", "T"
    }

    for i, line in enumerate(lines, 1):
        if not line:
            continue

        item_type = line[0]
        if item_type not in valid_types:
            errors.append(f"{filename}:{i} - Unbekannter Gopher-Item-Typ '{item_type}'")
            continue

        parts = line[1:].split("\t")
        if item_type == "i":
            # Info-Zeile
            if len(parts) < 1:
                errors.append(f"{filename}:{i} - Ungültige Info-Zeile.")
        else:
            # Navigationszeile: DisplayName, Selector, Host, Port
            if len(parts) < 4:
                errors.append(
                    f"{filename}:{i} - Gopher-Zeile erfordert 4 tab-getrennte Felder (Name, Selector, Host, Port). Gefunden: {len(parts)}"
                )

    return errors


def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    public_dir = root_dir / "public"

    if not public_dir.exists():
        print("[INFO] Verzeichnis 'public/' nicht gefunden. Überspringe...")
        sys.exit(0)

    total_errors = []
    checked_files = 0

    # Gemtext-Dateien prüfen
    for gmi_file in public_dir.glob("**/*.gmi"):
        checked_files += 1
        content = gmi_file.read_text(encoding="utf-8", errors="ignore")
        errs = validate_gemtext(content, str(gmi_file.relative_to(root_dir)))
        total_errors.extend(errs)

    # Gophermap-Dateien prüfen
    for gopher_file in public_dir.glob("**/gophermap"):
        checked_files += 1
        content = gopher_file.read_text(encoding="utf-8", errors="ignore")
        errs = validate_gophermap(content, str(gopher_file.relative_to(root_dir)))
        total_errors.extend(errs)

    print(f"[INFO] Gemini & Gopher Validator: {checked_files} Dateien geprüft.")

    if total_errors:
        print("\n[FEHLER] Validierungsfehler festgestellt:")
        for err in total_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[ERFOLG] Alle Gemtext- und Gophermap-Dateien sind protokollkonform.")
        sys.exit(0)


if __name__ == "__main__":
    main()
