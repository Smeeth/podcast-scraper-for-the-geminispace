# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import csv
import io
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db, init_db
from app.exporters import generate_gemtext_podcast, generate_gophermap_podcast
from app.gemini_service import GeminiAIService
from app.models import AIAnalysis, Episode, Podcast, Transcript
from app.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    EpisodeDetailResponse,
    EpisodeSummaryResponse,
    HealthResponse,
    PodcastDetailResponse,
    PodcastSummaryResponse,
    PublishResponse,
    ScrapeRequest,
    TranscriptResponse,
)
from app.scrapers.base import ScraperException
from app.scrapers.factory import ScraperFactory
from app.services.publisher import WebspacePublisher

# Logging-Konfiguration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("podcast_researcher")

gemini_service = GeminiAIService()
webspace_publisher = WebspacePublisher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisiert Ressourcen beim Start und räumt beim Herunterfahren auf."""
    logger.info("Starte Podcast & Media Channel Researcher Backend...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Konnte Datenbank beim Start nicht initialisieren: {e}")
    yield
    logger.info("Fahre Backend herunter...")


app = FastAPI(
    title="Podcast & Media Channel Researcher & AI Analyzer",
    description="Sicherheitsgehärtete API für Medien-Recherche, Archivierung und KI-Synthese (GPL-3.0)",
    version="1.0.0",
    lifespan=lifespan
)

# ==============================================================================
# Security Middleware (ADR-0001)
# ==============================================================================
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    return response


# CORS Konfiguration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ==============================================================================
# Health & Status Endpoints
# ==============================================================================
@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Healthcheck für Container-Orchestrierung und Monitoring."""
    db_status = "healthy"
    try:
        await db.execute(select(func.count(Podcast.id)))
    except Exception as e:
        db_status = f"unhealthy ({str(e)})"

    return HealthResponse(
        status="ok",
        database=db_status,
        gemini_available=gemini_service.is_configured(),
        gemini_model=settings.GEMINI_MODEL,
        environment=settings.ENVIRONMENT,
        version="1.0.0"
    )


# ==============================================================================
# Scraper & Podcast Management Endpoints
# ==============================================================================
@app.post("/api/scrape", response_model=PodcastDetailResponse, status_code=status.HTTP_201_CREATED, tags=["Scraper"])
async def scrape_media_feed(payload: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    """
    Importiert einen neuen Podcast, YouTube-Kanal oder RSS-Feed und persistiert alle Daten.
    """
    logger.info(f"Starte Scrape-Vorgang für URL: {payload.url}")

    try:
        scraper = ScraperFactory.get_scraper_for_url(payload.url)
        dto = await scraper.extract_podcast_and_episodes(
            url=payload.url,
            limit=payload.limit or 50,
            fetch_transcripts=payload.fetch_transcripts
        )
    except ScraperException as se:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(se)) from se
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Scraping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interner Verarbeitungsfehler beim Erfassen des Medien-Feeds."
        ) from e

    # Prüfen, ob Podcast bereits existiert (Update vs. Create)
    result = await db.execute(
        select(Podcast).where(
            (Podcast.url == dto.url) | (Podcast.feed_url == payload.url) | (Podcast.url == payload.url)
        )
    )
    podcast = result.scalar_one_or_none()

    if not podcast:
        podcast = Podcast(
            platform=dto.platform,
            title=dto.title,
            url=dto.url,
            feed_url=dto.feed_url,
            author=dto.author,
            description=dto.description,
            image_url=dto.image_url,
            metadata_json=dto.metadata
        )
        db.add(podcast)
        await db.flush()
    else:
        # Metadaten aktualisieren
        podcast.title = dto.title
        podcast.author = dto.author
        podcast.description = dto.description
        podcast.image_url = dto.image_url
        podcast.feed_url = dto.feed_url
        podcast.metadata_json = dto.metadata

    # Episoden abgleichen (inkl. Transkript-Status)
    existing_eps_res = await db.execute(
        select(Episode)
        .options(selectinload(Episode.transcript))
        .where(Episode.podcast_id == podcast.id)
    )
    existing_eps_map = {ep.external_id: ep for ep in existing_eps_res.scalars().all() if ep.external_id}

    for ep_dto in dto.episodes:
        if ep_dto.external_id in existing_eps_map:
            # Update existierende Episode
            existing_ep = existing_eps_map[ep_dto.external_id]
            existing_ep.title = ep_dto.title
            existing_ep.description = ep_dto.description
            existing_ep.duration_seconds = ep_dto.duration_seconds
            existing_ep.audio_or_video_url = ep_dto.audio_or_video_url
            existing_ep.chapters = [c.__dict__ for c in ep_dto.chapters]
            existing_ep.metadata_json = ep_dto.metadata

            # Transkript anfügen, falls zuvor nicht vorhanden
            if ep_dto.transcript and not existing_ep.transcript:
                new_transcript = Transcript(
                    episode_id=existing_ep.id,
                    language=ep_dto.transcript.language,
                    full_text=ep_dto.transcript.full_text,
                    segments=[s.__dict__ for s in ep_dto.transcript.segments]
                )
                db.add(new_transcript)
        else:
            # Neue Episode anlegen
            new_ep = Episode(
                podcast_id=podcast.id,
                external_id=ep_dto.external_id,
                title=ep_dto.title,
                episode_number=ep_dto.episode_number,
                published_at=ep_dto.published_at,
                duration_seconds=ep_dto.duration_seconds,
                description=ep_dto.description,
                audio_or_video_url=ep_dto.audio_or_video_url,
                chapters=[c.__dict__ for c in ep_dto.chapters],
                metadata_json=ep_dto.metadata
            )
            if ep_dto.transcript:
                new_transcript = Transcript(
                    language=ep_dto.transcript.language,
                    full_text=ep_dto.transcript.full_text,
                    segments=[s.__dict__ for s in ep_dto.transcript.segments]
                )
                new_ep.transcript = new_transcript
            db.add(new_ep)

    await db.commit()

    # Neu laden mit allen Beziehungen
    res = await db.execute(
        select(Podcast)
        .options(
            selectinload(Podcast.episodes).selectinload(Episode.transcript)
        )
        .where(Podcast.id == podcast.id)
    )
    saved_podcast = res.scalar_one()

    # DTO Response zusammenstellen
    ep_summaries = [
        EpisodeSummaryResponse(
            id=e.id,
            podcast_id=e.podcast_id,
            external_id=e.external_id,
            title=e.title,
            episode_number=e.episode_number,
            published_at=e.published_at,
            duration_seconds=e.duration_seconds,
            has_transcript=e.transcript is not None,
            has_chapters=bool(e.chapters and len(e.chapters) > 0),
            audio_or_video_url=e.audio_or_video_url
        )
        for e in saved_podcast.episodes
    ]

    return PodcastDetailResponse(
        id=saved_podcast.id,
        platform=saved_podcast.platform,
        title=saved_podcast.title,
        url=saved_podcast.url,
        feed_url=saved_podcast.feed_url,
        author=saved_podcast.author,
        description=saved_podcast.description,
        image_url=saved_podcast.image_url,
        metadata_json=saved_podcast.metadata_json,
        episodes=ep_summaries,
        created_at=saved_podcast.created_at,
        updated_at=saved_podcast.updated_at
    )


@app.get("/api/podcasts", response_model=list[PodcastSummaryResponse], tags=["Archiv"])
async def list_podcasts(db: AsyncSession = Depends(get_db)):
    """Liefert alle gespeicherten Podcasts / Kanäle im Recherche-Archiv."""
    stmt = (
        select(Podcast, func.count(Episode.id).label("episode_count"))
        .outerjoin(Episode, Podcast.id == Episode.podcast_id)
        .group_by(Podcast.id)
        .order_by(Podcast.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    podcasts_list = []
    for pod, count in rows:
        podcasts_list.append(PodcastSummaryResponse(
            id=pod.id,
            platform=pod.platform,
            title=pod.title,
            url=pod.url,
            feed_url=pod.feed_url,
            author=pod.author,
            description=pod.description,
            image_url=pod.image_url,
            episode_count=count,
            created_at=pod.created_at,
            updated_at=pod.updated_at
        ))
    return podcasts_list


@app.get("/api/podcasts/{podcast_id}", response_model=PodcastDetailResponse, tags=["Archiv"])
async def get_podcast_detail(podcast_id: str, db: AsyncSession = Depends(get_db)):
    """Liefert die Detailinformationen eines Podcasts inkl. aller Episoden."""
    stmt = (
        select(Podcast)
        .options(selectinload(Podcast.episodes).selectinload(Episode.transcript))
        .where(Podcast.id == podcast_id)
    )
    res = await db.execute(stmt)
    podcast = res.scalar_one_or_none()

    if not podcast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podcast nicht gefunden.")

    ep_summaries = [
        EpisodeSummaryResponse(
            id=e.id,
            podcast_id=e.podcast_id,
            external_id=e.external_id,
            title=e.title,
            episode_number=e.episode_number,
            published_at=e.published_at,
            duration_seconds=e.duration_seconds,
            has_transcript=e.transcript is not None,
            has_chapters=bool(e.chapters and len(e.chapters) > 0),
            audio_or_video_url=e.audio_or_video_url
        )
        for e in podcast.episodes
    ]

    return PodcastDetailResponse(
        id=podcast.id,
        platform=podcast.platform,
        title=podcast.title,
        url=podcast.url,
        feed_url=podcast.feed_url,
        author=podcast.author,
        description=podcast.description,
        image_url=podcast.image_url,
        metadata_json=podcast.metadata_json,
        episodes=ep_summaries,
        created_at=podcast.created_at,
        updated_at=podcast.updated_at
    )


@app.delete("/api/podcasts/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Archiv"])
async def delete_podcast(podcast_id: str, db: AsyncSession = Depends(get_db)):
    """Löscht einen Podcast und alle zugehörigen Episoden, Transkripte und Analysen kaskadierend."""
    res = await db.execute(select(Podcast).where(Podcast.id == podcast_id))
    podcast = res.scalar_one_or_none()
    if not podcast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podcast nicht gefunden.")

    await db.delete(podcast)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==============================================================================
# Episode & Transcript Endpoints
# ==============================================================================
@app.get("/api/episodes/{episode_id}", response_model=EpisodeDetailResponse, tags=["Episoden"])
async def get_episode_detail(episode_id: str, db: AsyncSession = Depends(get_db)):
    """Liefert alle Details, Show Notes, Kapitel und Transkript einer Folge."""
    stmt = (
        select(Episode)
        .options(selectinload(Episode.transcript))
        .where(Episode.id == episode_id)
    )
    res = await db.execute(stmt)
    episode = res.scalar_one_or_none()

    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode nicht gefunden.")

    transcript_resp = None
    if episode.transcript:
        transcript_resp = TranscriptResponse(
            id=episode.transcript.id,
            episode_id=episode.transcript.episode_id,
            language=episode.transcript.language,
            full_text=episode.transcript.full_text,
            segments=episode.transcript.segments or [],
            created_at=episode.transcript.created_at
        )

    return EpisodeDetailResponse(
        id=episode.id,
        podcast_id=episode.podcast_id,
        external_id=episode.external_id,
        title=episode.title,
        episode_number=episode.episode_number,
        published_at=episode.published_at,
        duration_seconds=episode.duration_seconds,
        description=episode.description,
        audio_or_video_url=episode.audio_or_video_url,
        chapters=episode.chapters or [],
        metadata_json=episode.metadata_json,
        transcript=transcript_resp,
        created_at=episode.created_at
    )


@app.post("/api/episodes/{episode_id}/transcript", response_model=TranscriptResponse, tags=["Episoden"])
async def fetch_episode_transcript(episode_id: str, db: AsyncSession = Depends(get_db)):
    """Ruft das Transkript für eine Episode on-demand ab."""
    stmt = (
        select(Episode)
        .options(selectinload(Episode.transcript), selectinload(Episode.podcast))
        .where(Episode.id == episode_id)
    )
    res = await db.execute(stmt)
    episode = res.scalar_one_or_none()

    if not episode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode nicht gefunden.")

    if episode.transcript:
        return TranscriptResponse.model_validate(episode.transcript)

    # Scraper ermitteln
    scraper = ScraperFactory.get_scraper_for_url(episode.podcast.url)
    target_id = episode.external_id or episode.audio_or_video_url or ""
    transcript_dto = await scraper.extract_transcript(target_id)

    if not transcript_dto or not transcript_dto.full_text:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Für diese Folge konnte kein Transkript gefunden werden."
        )

    new_transcript = Transcript(
        episode_id=episode.id,
        language=transcript_dto.language,
        full_text=transcript_dto.full_text,
        segments=[s.__dict__ for s in transcript_dto.segments]
    )
    db.add(new_transcript)
    await db.commit()
    await db.refresh(new_transcript)

    return TranscriptResponse(
        id=new_transcript.id,
        episode_id=new_transcript.episode_id,
        language=new_transcript.language,
        full_text=new_transcript.full_text,
        segments=new_transcript.segments or [],
        created_at=new_transcript.created_at
    )


# ==============================================================================
# Gemini AI Lab Endpoints
# ==============================================================================
@app.post("/api/ai/analyze", response_model=AIAnalysisResponse, tags=["Gemini AI"])
async def run_ai_analysis(payload: AIAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """
    Führt eine strukturierte Gemini KI-Analyse durch (Wikipedia-Tabelle, Gäste/Themen, Q&A, Chat).
    """
    # Podcast & Episoden laden
    stmt = (
        select(Podcast)
        .options(selectinload(Podcast.episodes).selectinload(Episode.transcript))
        .where(Podcast.id == payload.podcast_id)
    )
    res = await db.execute(stmt)
    podcast = res.scalar_one_or_none()

    if not podcast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podcast nicht gefunden.")

    pod_dict = {
        "title": podcast.title,
        "platform": podcast.platform,
        "author": podcast.author,
        "description": podcast.description
    }

    episodes_list = []
    selected_transcript = None

    for ep in podcast.episodes:
        ep_dict = {
            "title": ep.title,
            "episode_number": ep.episode_number,
            "published_at": ep.published_at.isoformat() if ep.published_at else "",
            "duration_seconds": ep.duration_seconds,
            "description": ep.description
        }
        episodes_list.append(ep_dict)

        if payload.episode_id and ep.id == payload.episode_id and ep.transcript:
            selected_transcript = ep.transcript.full_text

    analysis_res = await gemini_service.generate_analysis(
        analysis_type=payload.analysis_type,
        podcast_info=pod_dict,
        episodes=episodes_list,
        transcript_text=selected_transcript,
        custom_query=payload.custom_query,
        model_override=payload.model
    )

    # Persistieren der Analyse
    ai_record = AIAnalysis(
        podcast_id=podcast.id,
        episode_id=payload.episode_id,
        analysis_type=payload.analysis_type,
        prompt=analysis_res.get("prompt", ""),
        model=analysis_res.get("model", settings.GEMINI_MODEL),
        response_text=analysis_res.get("response_text", ""),
        metadata_json={"success": analysis_res.get("success", False)}
    )
    db.add(ai_record)
    await db.commit()
    await db.refresh(ai_record)

    return AIAnalysisResponse(
        id=ai_record.id,
        podcast_id=ai_record.podcast_id,
        episode_id=ai_record.episode_id,
        analysis_type=ai_record.analysis_type,
        prompt=ai_record.prompt,
        model=ai_record.model,
        response_text=ai_record.response_text,
        created_at=ai_record.created_at
    )


@app.get("/api/ai/history/{podcast_id}", response_model=list[AIAnalysisResponse], tags=["Gemini AI"])
async def get_ai_history(podcast_id: str, db: AsyncSession = Depends(get_db)):
    """Gibt frühere KI-Analysen für einen Podcast zurück."""
    stmt = (
        select(AIAnalysis)
        .where(AIAnalysis.podcast_id == podcast_id)
        .order_by(AIAnalysis.created_at.desc())
    )
    res = await db.execute(stmt)
    analyses = res.scalars().all()

    return [
        AIAnalysisResponse(
            id=a.id,
            podcast_id=a.podcast_id,
            episode_id=a.episode_id,
            analysis_type=a.analysis_type,
            prompt=a.prompt,
            model=a.model,
            response_text=a.response_text,
            created_at=a.created_at
        )
        for a in analyses
    ]


# ==============================================================================
# Export Center Endpoints
# ==============================================================================
@app.get("/api/export/{podcast_id}", tags=["Export"])
async def export_podcast_data(
    podcast_id: str,
    export_format: str = Query("json", alias="format", pattern="^(csv|json|markdown|wikitext|gemtext|gopher)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exportiert die Episoden- und Recherche-Daten eines Podcasts in CSV, JSON, Markdown, Wikitext, Gemtext (.gmi) oder Gophermap.
    """
    stmt = (
        select(Podcast)
        .options(selectinload(Podcast.episodes))
        .where(Podcast.id == podcast_id)
    )
    res = await db.execute(stmt)
    podcast = res.scalar_one_or_none()

    if not podcast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podcast nicht gefunden.")

    safe_title = "".join(c for c in podcast.title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")

    if export_format == "json":
        data = {
            "title": podcast.title,
            "platform": podcast.platform,
            "url": podcast.url,
            "author": podcast.author,
            "description": podcast.description,
            "episodes": [
                {
                    "number": ep.episode_number,
                    "title": ep.title,
                    "published_at": ep.published_at.isoformat() if ep.published_at else None,
                    "duration_seconds": ep.duration_seconds,
                    "description": ep.description,
                    "audio_or_video_url": ep.audio_or_video_url,
                    "chapters": ep.chapters
                }
                for ep in podcast.episodes
            ]
        }
        return Response(
            content=json.dumps(data, indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.json"'}
        )

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Episode", "Titel", "Veroeffentlichung", "Dauer_Minuten", "URL", "Show_Notes"])
        for ep in podcast.episodes:
            dur_min = round(ep.duration_seconds / 60, 1) if ep.duration_seconds else ""
            pub = ep.published_at.strftime("%Y-%m-%d") if ep.published_at else ""
            clean_desc = (ep.description or "").replace("\n", " ")[:300]
            writer.writerow([
                ep.episode_number or "",
                ep.title,
                pub,
                dur_min,
                ep.audio_or_video_url or "",
                clean_desc
            ])
        return Response(
            content=output.getvalue().encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.csv"'}
        )

    if export_format == "markdown":
        md = [
            f"# {podcast.title}",
            f"**Plattform:** {podcast.platform.upper()} | **Autor:** {podcast.author or 'Unbekannt'}",
            f"**URL:** {podcast.url}\n",
            f"## Beschreibung\n{podcast.description or 'Keine Beschreibung vorhanden.'}\n",
            "## Episodenliste\n",
            "| Nr. | Titel | Datum | Dauer | Link |",
            "|---|---|---|---|---|"
        ]
        for ep in podcast.episodes:
            dur = f"{ep.duration_seconds // 60}m" if ep.duration_seconds else "-"
            pub = ep.published_at.strftime("%Y-%m-%d") if ep.published_at else "-"
            url_link = f"[Link]({ep.audio_or_video_url})" if ep.audio_or_video_url else "-"
            md.append(f"| {ep.episode_number or '-'} | {ep.title} | {pub} | {dur} | {url_link} |")

        return Response(
            content="\n".join(md),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'}
        )

    if export_format == "wikitext":
        wiki = [
            f"== {podcast.title} ==",
            f"'''Autor/Kanal:''' {podcast.author or 'Unbekannt'}",
            f"'''Offizielle URL:''' [{podcast.url} {podcast.title}]",
            "",
            '{| class="wikitable sortable" style="font-size: 95%;"',
            "! Nr. !! Titel !! Erstveröffentlichung !! Dauer !! Link",
            "|-"
        ]
        for ep in podcast.episodes:
            dur = f"{ep.duration_seconds // 60} Min." if ep.duration_seconds else "-"
            pub = ep.published_at.strftime("%d.%m.%Y") if ep.published_at else "-"
            link_str = f"[{ep.audio_or_video_url} Link]" if ep.audio_or_video_url else "-"
            wiki.append(f"| {ep.episode_number or '-'} || {ep.title} || {pub} || {dur} || {link_str}")
            wiki.append("|-")
        wiki.append("|}")

        return Response(
            content="\n".join(wiki),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}_wikitext.txt"'}
        )

    if export_format == "gemtext":
        gemtext_content = generate_gemtext_podcast(podcast)
        return Response(
            content=gemtext_content,
            media_type="text/gemini; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.gmi"'}
        )

    if export_format == "gopher":
        gopher_content = generate_gophermap_podcast(
            podcast, host=settings.GOPHER_HOST, port=settings.GOPHER_PORT
        )
        return Response(
            content=gopher_content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.gophermap"'}
        )
    return None


# ==============================================================================
# Webspace Publisher Endpoints (Geminispace & Gopherspace)
# ==============================================================================
@app.post("/api/publish", response_model=PublishResponse, tags=["Webspaces"])
async def publish_webspaces(db: AsyncSession = Depends(get_db)):
    """
    Generiert und publiziert alle archivierten Podcasts als statische Webspaces
    unter `public/gemini` (text/gemini .gmi) und `public/gopher` (gophermap).
    """
    stmt = (
        select(Podcast)
        .options(selectinload(Podcast.episodes))
        .order_by(Podcast.updated_at.desc())
    )
    res = await db.execute(stmt)
    podcasts = res.scalars().all()

    result = webspace_publisher.publish_all(podcasts)
    return PublishResponse(**result)


@app.get("/api/publish/status", tags=["Webspaces"])
async def get_publish_status():
    """Liefert den aktuellen Status der publizierten Webspaces unter public/gemini und public/gopher."""
    return webspace_publisher.get_status()


# ==============================================================================
# Static Files Mount (Frontend)
# ==============================================================================
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
