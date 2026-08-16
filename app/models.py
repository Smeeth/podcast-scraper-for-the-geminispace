# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """Erzeugt eine eindeutige UUID als String."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Gibt den aktuellen UTC-Zeitstempel zurück."""
    return datetime.now(UTC)


class Podcast(Base):
    """
    Repräsentiert einen Podcast, YouTube-Kanal oder Medien-Feed.
    """
    __tablename__ = "podcasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'youtube', 'rss', 'apple'
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True, index=True)
    feed_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Beziehungen
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="podcast",
        cascade="all, delete-orphan",
        order_by="desc(Episode.published_at)"
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis",
        back_populates="podcast",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_podcasts_platform_title", "platform", "title"),
    )


class Episode(Base):
    """
    Repräsentiert eine einzelne Folge eines Podcasts oder ein Video.
    """
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    podcast_id: Mapped[str] = mapped_column(String(36), ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # Show Notes
    audio_or_video_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    chapters: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, default=list)  # Liste von Kapiteln mit Timestamps
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    podcast: Mapped["Podcast"] = relationship("Podcast", back_populates="episodes")
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript",
        back_populates="episode",
        cascade="all, delete-orphan",
        uselist=False
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis",
        back_populates="episode",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_episodes_podcast_published", "podcast_id", "published_at"),
    )


class Transcript(Base):
    """
    Repräsentiert das vollständige Transkript einer Folge inkl. Zeitstempel-Segmenten.
    """
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True, default="de")
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    segments: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, default=list)  # [{'start': 0.0, 'duration': 3.2, 'text': '...'}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    episode: Mapped["Episode"] = relationship("Episode", back_populates="transcript")


class AIAnalysis(Base):
    """
    Repräsentiert ein persistiertes Ergebnis einer Gemini KI-Recherche oder Analyse.
    """
    __tablename__ = "ai_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    podcast_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=True, index=True)
    episode_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'wikitext_table', 'guests_topics', 'qa', 'custom_chat', 'summary'
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    podcast: Mapped["Podcast | None"] = relationship("Podcast", back_populates="ai_analyses")
    episode: Mapped["Episode | None"] = relationship("Episode", back_populates="ai_analyses")
