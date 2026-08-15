# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import logging
import asyncio
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

# Versuche google-genai zu importieren
try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False
    logger.warning("google-genai SDK nicht installiert. KI-Funktionen stehen nur eingeschränkt zur Verfügung.")


SYSTEM_INSTRUCTION = """Du bist ein hochpräziser Recherche- und Medienanalyst für Podcasts, YouTube-Kanäle und journalistische Formate.
Deine Aufgaben sind:
1. Genaue Extraktion von Fakten, Gästen, Themen und Zeitstempeln aus den bereitgestellten Show Notes, Metadaten und Transkripten.
2. Keine Halluzinationen: Antworte nur basierend auf den bereitgestellten Kontextdaten oder weise transparent darauf hin, wenn Informationen fehlen.
3. Wenn Wikitext angefordert wird, erstelle saubere, standardkonforme MediaWiki-Syntax ({| class="wikitable sortable" ... |}).
4. Formatiere strukturierte Ausgaben mit klaren Überschriften, Markdown-Tabellen oder Aufzählungen.
"""


class GeminiAIService:
    """
    Sicherheitsgehärteter Gemini AI Service mit Prompt-Templates und Token-Management.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY if settings.is_gemini_available() else None
        self.client = None
        if self.api_key and GENAI_SDK_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Fehler bei der Initialisierung des Gemini Clients: {e}")

    def is_configured(self) -> bool:
        """Prüft, ob der Gemini Service betriebsbereit ist."""
        return bool(self.client is not None or (self.api_key and GENAI_SDK_AVAILABLE))

    def _get_client(self):
        """Lazy Initialisierung des Google GenAI Clients."""
        if not self.client and self.api_key and GENAI_SDK_AVAILABLE:
            self.client = genai.Client(api_key=self.api_key)
        return self.client

    def _build_context_text(
        self,
        podcast_info: Dict[str, Any],
        episodes: List[Dict[str, Any]],
        transcript_text: Optional[str] = None
    ) -> str:
        """
        Kombiniert Metadaten, Episoden und Transkripte zu einem optimierten Kontext-String.
        """
        parts = [
            f"# MEDIEN-KANAL: {podcast_info.get('title', 'Unbekannt')}",
            f"Plattform: {podcast_info.get('platform', '').upper()}",
            f"Autor / Host: {podcast_info.get('author', 'Unbekannt')}",
            f"Beschreibung: {podcast_info.get('description', '')[:1000]}",
            "\n## EPISODEN-ÜBERSICHT:\n"
        ]

        for ep in episodes[:50]:  # Bis zu 50 Episoden für den Kontext
            dur_min = (ep.get('duration_seconds') or 0) // 60
            pub = ep.get('published_at') or 'Unbekannt'
            parts.append(
                f"- Folge {ep.get('episode_number') or '#'}: '{ep.get('title')}' "
                f"(Datum: {pub}, Dauer: {dur_min} min)\n"
                f"  Show Notes: {ep.get('description', '')[:500]}"
            )

        if transcript_text:
            parts.append(f"\n## VOLLSTÄNDIGES TRANSKRIPT DER AUSGEWÄHLTEN FOLGE:\n{transcript_text[:50000]}")

        return "\n".join(parts)

    def _build_prompt(
        self,
        analysis_type: str,
        context: str,
        custom_query: Optional[str] = None
    ) -> str:
        """
        Erstellt den zielgerichteten Prompt basierend auf dem Analysetyp.
        """
        if analysis_type == "wikitext_table":
            return f"""Erstelle eine standardkonforme Wikipedia-Episodentabelle (MediaWiki Wikitext) für den folgenden Podcast/Kanal.

Format-Vorgaben:
- Verwende `{{| class="wikitable sortable" style="font-size: 95%;"`.
- Spalten: `! Nr. !! Titel !! Erstveröffentlichung !! Dauer !! Gäste / Beteiligte !! Kurzzusammenfassung`
- Extrahiere die Informationen präzise aus dem Kontext.
- Schließe die Tabelle mit `|}}` ab.
- Gib AUSSCHLIESSLICH den Wikitext-Codeblock und eine kurze Zusammenfassung aus.

KONTEXT-DATEN:
{context}
"""

        elif analysis_type == "guests_topics":
            return f"""Analysiere den folgenden Podcast/Kanal und erstelle ein detailliertes Profil aller Gäste, Rollen und Hauptthemen.

Gliedere deine Antwort in:
1. 👥 **Gäste & Experten:** Name, Funktion/Organisation, behandelte Themen, relevante Zitate/Thesen.
2. 📌 **Hauptthemen & Thematische Schwerpunkte:** Zusammenfassung der Kerninhalte nach Episoden.
3. ⏱️ **Schlüssel-Momente & Kontroversen:** Bemerkenswerte Thesen oder Diskussionspunkte.

KONTEXT-DATEN:
{context}
"""

        elif analysis_type == "qa":
            query = custom_query or "Fasse die wichtigsten Kernaussagen zusammen."
            return f"""Beantworte die folgende Frage präzise und belegt auf Basis der bereitgestellten Podcast-Daten und Transkripte.

FRAGE DES RECHERCHIERENDEN:
{query}

KONTEXT-DATEN:
{context}

ANWEISUNG:
Gib genaue Zeitstempel oder Episodentitel an, wenn du Aussagen belegst. Halluziniere keine Fakten.
"""

        elif analysis_type == "summary":
            return f"""Erstelle eine hochstrukturierte Executive Summary für diesen Podcast/Kanal.

Inhalte:
1. **Kanalprofil & Ausrichtung:** Zielgruppe, Format, Tonalität.
2. **Top-Themenfelder:** Welche übergeordneten Debatten werden geführt?
3. **Wichtigste Erkenntnisse & Takeaways.**

KONTEXT-DATEN:
{context}
"""

        else:  # custom_chat / freier Dialog
            prompt_body = custom_query or "Analysiere die vorliegenden Episoden und hebe Besonderheiten hervor."
            return f"""{prompt_body}

KONTEXT-DATEN:
{context}
"""

    async def generate_analysis(
        self,
        analysis_type: str,
        podcast_info: Dict[str, Any],
        episodes: List[Dict[str, Any]],
        transcript_text: Optional[str] = None,
        custom_query: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Führt die KI-Analyse mit Google Gemini asynchron aus.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Gemini API-Key ist nicht konfiguriert. Bitte hinterlege deinen GEMINI_API_KEY in der .env-Datei.",
                "response_text": (
                    "⚠️ **Hinweis:** Der Gemini AI Service ist aktuell nicht aktiv.\n\n"
                    "Um KI-Analysen (Wikipedia-Tabellen, Gäste-Extraktion, Q&A) zu nutzen:\n"
                    "1. Öffne die `.env` Datei im Projektverzeichnis.\n"
                    "2. Trage deinen `GEMINI_API_KEY` ein.\n"
                    "3. Starte den Container oder Backend-Dienst neu."
                ),
                "model": "none",
                "prompt": ""
            }

        context = self._build_context_text(podcast_info, episodes, transcript_text)
        prompt = self._build_prompt(analysis_type, context, custom_query)
        model_name = model_override or settings.GEMINI_MODEL

        def _call_gemini_sync() -> str:
            client = self._get_client()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,  # Niedrige Temperatur für hohe Faktentreue
                )
            )
            return response.text if response and response.text else "Keine Antwort von Gemini erhalten."

        try:
            response_text = await asyncio.to_thread(_call_gemini_sync)
            return {
                "success": True,
                "model": model_name,
                "prompt": prompt[:500] + "...",
                "response_text": response_text
            }
        except Exception as e:
            logger.error(f"Fehler bei Gemini API-Aufruf: {e}")
            return {
                "success": False,
                "error": f"Fehler bei der Kommunikation mit Google Gemini: {str(e)}",
                "response_text": f"❌ Fehler bei der KI-Analyse: {str(e)}",
                "model": model_name,
                "prompt": prompt[:500] + "..."
            }
