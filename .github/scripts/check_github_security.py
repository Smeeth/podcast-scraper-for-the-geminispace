# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

"""
Prüfskript für GitHub Sicherheitsberichte (CodeQL, Dependabot, Secret Scanning).
Liest das GITHUB_TOKEN automatisch aus der lokalen .env-Datei oder Umgebungsvariablen.
"""

import os
import sys

import httpx
from dotenv import dotenv_values


def main() -> int:
    env_vars = dotenv_values(".env") if os.path.exists(".env") else {}
    token = (
        os.getenv("GITHUB_TOKEN")
        or env_vars.get("GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or env_vars.get("GH_TOKEN")
    )

    if not token:
        print("[WARNUNG] Kein GITHUB_TOKEN in der .env-Datei oder Umgebung gefunden.")
        print("          Überspringe GitHub API Security-Check.")
        return 0

    owner_repo = "Smeeth/podcast-scraper-for-the-geminispace"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PodcastResearcher-SecurityAudit/1.0",
    }

    print(f"[INFO] GitHub Security Audit für Repository: {owner_repo}")
    total_issues = 0

    with httpx.Client(headers=headers, timeout=15.0) as client:
        # 1. Code Scanning / CodeQL
        try:
            res = client.get(f"https://api.github.com/repos/{owner_repo}/code-scanning/alerts?state=open")
            if res.status_code == 200:
                alerts = res.json()
                print(f"[INFO] Code Scanning (CodeQL): {len(alerts)} offene Alerts.")
                for a in alerts:
                    total_issues += 1
                    rule = a.get("rule", {})
                    inst = a.get("most_recent_instance", {})
                    loc = inst.get("location", {})
                    sev = rule.get("security_severity_level") or rule.get("severity") or "unknown"
                    path = loc.get("path", "unknown")
                    line = loc.get("start_line", "?")
                    print(f"  - Alert #{a.get('number')} [{sev.upper()}]: {rule.get('id')} ({path}:{line})")
                    print(f"    {inst.get('message', {}).get('text')}")
            elif res.status_code == 404:
                print("[INFO] Code Scanning: Keine Alerts oder nicht aktiviert.")
            elif res.status_code == 403:
                print("[HINWEIS] Code Scanning API: Zugriff verweigert (403).")
            else:
                print(f"[WARNUNG] Code Scanning API Status: {res.status_code}")
        except Exception as e:
            print(f"[FEHLER] Code Scanning Abfrage fehlgeschlagen: {e}")

        # 2. Dependabot Alerts
        try:
            res = client.get(f"https://api.github.com/repos/{owner_repo}/dependabot/alerts?state=open")
            if res.status_code == 200:
                alerts = res.json()
                print(f"[INFO] Dependabot: {len(alerts)} offene Alerts.")
                for a in alerts:
                    total_issues += 1
                    adv = a.get("security_advisory", {})
                    dep = a.get("dependency", {}).get("package", {}).get("name", "unknown")
                    sev = adv.get("severity", "unknown")
                    print(f"  - Alert #{a.get('number')} [{sev.upper()}]: {dep} - {adv.get('summary')}")
            elif res.status_code == 404:
                print("[INFO] Dependabot: Keine Alerts oder nicht aktiviert.")
            elif res.status_code == 403:
                print("[HINWEIS] Dependabot API: Zugriff nicht freigegeben (403).")
            else:
                print(f"[WARNUNG] Dependabot API Status: {res.status_code}")
        except Exception as e:
            print(f"[FEHLER] Dependabot Abfrage fehlgeschlagen: {e}")

        # 3. Secret Scanning
        try:
            res = client.get(f"https://api.github.com/repos/{owner_repo}/secret-scanning/alerts?state=open")
            if res.status_code == 200:
                alerts = res.json()
                print(f"[INFO] Secret Scanning: {len(alerts)} offene Alerts.")
                for alert in alerts:
                    total_issues += 1
                    alert_id = int(alert.get("number", 0))
                    alert_state = str(alert.get("state", "open")).strip()
                    # CWE-532 / CodeQL: Prevent logging dynamic secret scanning fields in console
                    print(f"  - Secret Alert #{alert_id} [Status: {alert_state}]")
            elif res.status_code == 404:
                print("[INFO] Secret Scanning: Keine Alerts.")
            elif res.status_code == 403:
                print("[HINWEIS] Secret Scanning API: Zugriff nicht freigegeben (403).")
            else:
                print(f"[WARNUNG] Secret Scanning API Status: {res.status_code}")
        except Exception as e:
            print(f"[FEHLER] Secret Scanning Abfrage fehlgeschlagen: {e}")

    if total_issues == 0:
        print("[ERFOLG] Alle überprüften GitHub Security Audits sind sauber (0 offene Alerts).")
    else:
        print(f"[STATUS] Insgesamt {total_issues} offene Sicherheitsberichte auf GitHub vorhanden.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
