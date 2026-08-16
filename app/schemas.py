# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import is_safe_external_url


# ==============================================================================
# Scraper & Ingestion Schemas
# ==============================================================================
class ProbeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL des Feeds oder YouTube Kanals zur schnellen Vorab-Prüfung",
        min_length=5,
        max_length=2048
    )

    @field_validator("url")
    @classmethod
    def validate_url_security(cls, v: str) -> str:
        is_safe, error_msg = is_safe_external_url(v)
        if not is_safe:
            raise ValueError(f"Sicherheitsüberprüfung fehlgeschlagen: {error_msg}")
        return v.strip()


class ProbeResponse(BaseModel):
    platform: str
    title: str
    url: str
    author: str | None = None
    description: str | None = None
    image_url: str | None = None
    approx_episodes_count: int | None = None
    metadata: dict[str, Any] = {}


class ScrapeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL des RSS-Feeds, Apple Podcasts Links oder YouTube Kanals/Playlists/Videos",
        min_length=5,
        max_length=2048
    )
    limit: int | None = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximale Anzahl der zu importierenden Episoden"
    )
    fetch_transcripts: bool = Field(
        default=False,
        description="Gibt an, ob Transkripte direkt beim Import geladen werden sollen"
    )

    @field_validator("url")
    @classmethod
    def validate_url_security(cls, v: str) -> str:
        is_safe, error_msg = is_safe_external_url(v)
        if not is_safe:
            raise ValueError(f"Sicherheitsüberprüfung fehlgeschlagen: {error_msg}")
        return v.strip()



# ==============================================================================
# Chapter & Transcript DTOs
# ==============================================================================
class ChapterItem(BaseModel):
    title: str
    start_time: float = Field(..., ge=0)
    start_time_formatted: str | None = None


class TranscriptSegmentItem(BaseModel):
    start: float = Field(..., ge=0)
    duration: float = Field(..., ge=0)
    text: str


class TranscriptResponse(BaseModel):
    id: str
    episode_id: str
    language: str | None = "de"
    full_text: str
    segments: list[TranscriptSegmentItem] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranscriptSearchResultItem(BaseModel):
    podcast_id: str
    podcast_title: str
    episode_id: str
    episode_title: str
    episode_number: int | None = None
    timestamp_seconds: float
    timestamp_formatted: str
    matched_text: str
    deep_link_url: str | None = None


class TranscriptSearchResponse(BaseModel):
    query: str
    total_matches: int
    results: list[TranscriptSearchResultItem]



# ==============================================================================
# Episode Schemas
# ==============================================================================
class EpisodeSummaryResponse(BaseModel):
    id: str
    podcast_id: str
    external_id: str | None = None
    title: str
    episode_number: int | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    has_transcript: bool = False
    has_chapters: bool = False
    audio_or_video_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EpisodeDetailResponse(BaseModel):
    id: str
    podcast_id: str
    external_id: str | None = None
    title: str
    episode_number: int | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    description: str | None = None
    audio_or_video_url: str | None = None
    chapters: list[dict[str, Any]] = []
    metadata_json: dict[str, Any] | None = None
    transcript: TranscriptResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Podcast Schemas
# ==============================================================================
class PodcastSummaryResponse(BaseModel):
    id: str
    platform: str
    title: str
    url: str
    feed_url: str | None = None
    author: str | None = None
    description: str | None = None
    image_url: str | None = None
    episode_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PodcastDetailResponse(BaseModel):
    id: str
    platform: str
    title: str
    url: str
    feed_url: str | None = None
    author: str | None = None
    description: str | None = None
    image_url: str | None = None
    metadata_json: dict[str, Any] | None = None
    episodes: list[EpisodeSummaryResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Gemini AI Analysis Schemas
# ==============================================================================
class AIAnalysisRequest(BaseModel):
    podcast_id: str
    episode_id: str | None = None
    analysis_type: str = Field(
        ...,
        description="Typ der Analyse: 'wikitext_table', 'wikipedia_template', 'guests_topics', 'qa', 'custom_chat', 'summary'"
    )
    custom_query: str | None = Field(
        default=None,
        description="Spezifische Frage für Q&A oder Prompt für freien Chat"
    )
    style_format: str | None = Field(
        default="wikitable",
        description="Stilformat für Wikipedia-Generierung ('wikitable' oder 'template')"
    )
    only_new_episodes: bool = Field(
        default=False,
        description="Falls True, werden nur die neuesten Episoden im Delta-Modus aufbereitet"
    )
    model: str | None = None

    @field_validator("analysis_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {
            "wikitext_table",
            "wikipedia_template",
            "guests_topics",
            "qa",
            "custom_chat",
            "summary",
        }
        if v not in valid_types:
            raise ValueError(f"Ungültiger Analysetyp '{v}'. Erlaubt: {', '.join(sorted(valid_types))}")
        return v



class AIAnalysisResponse(BaseModel):
    id: str
    podcast_id: str | None = None
    episode_id: str | None = None
    analysis_type: str
    prompt: str
    model: str
    response_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# System & Status Schemas
# ==============================================================================
class HealthResponse(BaseModel):
    status: str = "ok"
    database: str
    gemini_available: bool
    gemini_model: str
    environment: str
    version: str = "1.0.0"


class PublishResponse(BaseModel):
    success: bool
    podcast_count: int
    gemini_files_count: int
    gopher_files_count: int
    gemini_directory: str
    gopher_directory: str
    gemini_index: str
    gopher_index: str

