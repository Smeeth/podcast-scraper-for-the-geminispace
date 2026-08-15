# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.config import is_safe_external_url


# ==============================================================================
# Scraper & Ingestion Schemas
# ==============================================================================
class ScrapeRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL des RSS-Feeds, Apple Podcasts Links oder YouTube Kanals/Playlists/Videos",
        min_length=5,
        max_length=2048
    )
    limit: Optional[int] = Field(
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
    start_time_formatted: Optional[str] = None


class TranscriptSegmentItem(BaseModel):
    start: float = Field(..., ge=0)
    duration: float = Field(..., ge=0)
    text: str


class TranscriptResponse(BaseModel):
    id: str
    episode_id: str
    language: Optional[str] = "de"
    full_text: str
    segments: List[TranscriptSegmentItem] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Episode Schemas
# ==============================================================================
class EpisodeSummaryResponse(BaseModel):
    id: str
    podcast_id: str
    external_id: Optional[str] = None
    title: str
    episode_number: Optional[int] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    has_transcript: bool = False
    has_chapters: bool = False
    audio_or_video_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EpisodeDetailResponse(BaseModel):
    id: str
    podcast_id: str
    external_id: Optional[str] = None
    title: str
    episode_number: Optional[int] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    description: Optional[str] = None
    audio_or_video_url: Optional[str] = None
    chapters: List[Dict[str, Any]] = []
    metadata_json: Optional[Dict[str, Any]] = None
    transcript: Optional[TranscriptResponse] = None
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
    feed_url: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    episode_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PodcastDetailResponse(BaseModel):
    id: str
    platform: str
    title: str
    url: str
    feed_url: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    episodes: List[EpisodeSummaryResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Gemini AI Analysis Schemas
# ==============================================================================
class AIAnalysisRequest(BaseModel):
    podcast_id: str
    episode_id: Optional[str] = None
    analysis_type: str = Field(
        ...,
        description="Typ der Analyse: 'wikitext_table', 'guests_topics', 'qa', 'custom_chat', 'summary'"
    )
    custom_query: Optional[str] = Field(
        default=None,
        description="Spezifische Frage für Q&A oder Prompt für freien Chat"
    )
    model: Optional[str] = None

    @field_validator("analysis_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {"wikitext_table", "guests_topics", "qa", "custom_chat", "summary"}
        if v not in valid_types:
            raise ValueError(f"Ungültiger Analysetyp '{v}'. Erlaubt: {', '.join(sorted(valid_types))}")
        return v


class AIAnalysisResponse(BaseModel):
    id: str
    podcast_id: Optional[str] = None
    episode_id: Optional[str] = None
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

