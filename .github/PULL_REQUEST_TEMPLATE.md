## 📋 Beschreibung der Änderungen
<!-- Beschreibe kurz, welches Problem gelöst oder welches Feature implementiert wurde -->

## 🛡️ Einhaltung der Sicherheitsarchitektur (ADR-0001)
- [ ] **Security > Performance > Usability** wurde bei allen Änderungen berücksichtigt.
- [ ] Sämtliche Benutzereingaben und externe URLs werden strikt validiert (Pydantic v2 / SSRF-Schutz).
- [ ] Keine sensiblen API-Keys, Tokens oder Passwörter in Code, Logs oder Fehlermeldungen.
- [ ] XML-Dateien werden ausschließlich über `defusedxml` verarbeitet.
- [ ] Alle Datenbankabfragen sind typisiert und nutzen parametrisierte SQLAlchemy 2.0 Async Queries.

## ⚖️ Lizenzierung & Living Agent Documentation
- [ ] Alle neuen Quellcodedateien besitzen den standardisierten SPDX-Header (`SPDX-License-Identifier: GPL-3.0-or-later`).
- [ ] Änderungen an Modulgrenzen oder Architektur sind in `.agents/ARCHITECTURE.md` und `.agents/CONTEXT.md` synchronisiert.
- [ ] Neue Architektur-Entscheidungen sind als ADR unter `.agents/DECISIONS/` dokumentiert.

## 🧪 Tests & Verifikation
- [ ] Neue Unit- oder Integrationstests wurden unter `tests/` ergänzt.
- [ ] Lokale Test-Suite erfolgreich ausgeführt: `python -m unittest discover -s tests -v`
- [ ] CI-Verifikationsskripte erfolgreich ausgeführt:
  - `python .github/scripts/verify_spdx_headers.py`
  - `python .github/scripts/gemtext_validator.py`
  - `python .github/scripts/security_audit.py`
