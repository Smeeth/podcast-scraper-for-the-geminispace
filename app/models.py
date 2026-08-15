# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    """Erzeugt eine eindeutige UUID als String."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Gibt den aktuellen UTC-Zeitstempel zurück."""
    return datetime.now(timezone.utc)


class Podcast(Base):
    """
    Repräsentiert einen Podcast, YouTube-Kanal oder Medien-Feed.
    """
    __tablename__ = "podcasts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    platform = Column(String(50), nullable=False, index=True)  # 'youtube', 'rss', 'apple'
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(2048), nullable=False, unique=True, index=True)
    feed_url = Column(String(2048), nullable=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(2048), nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Beziehungen
    episodes = relationship(
        "Episode",
        back_populates="podcast",
        cascade="all, delete-orphan",
        order_by="desc(Episode.published_at)"
    )
    ai_analyses = relationship(
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

    id = Column(String(36), primary_key=True, default=generate_uuid)
    podcast_id = Column(String(36), ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    episode_number = Column(Integer, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)  # Show Notes
    audio_or_video_url = Column(String(2048), nullable=True)
    chapters = Column(JSON, nullable=True, default=list)  # Liste von Kapiteln mit Timestamps
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    podcast = relationship("Podcast", back_populates="episodes")
    transcript = relationship(
        "Transcript",
        uselist=False,
        back_populates="episode",
        cascade="all, delete-orphan"
    )
    ai_analyses = relationship(
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

    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    language = Column(String(20), nullable=True, default="de")
    full_text = Column(Text, nullable=False)
    segments = Column(JSON, nullable=True, default=list)  # [{'start': 0.0, 'duration': 3.2, 'text': '...'}]
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    episode = relationship("Episode", back_populates="transcript")


class AIAnalysis(Base):
    """
    Repräsentiert ein persistiertes Ergebnis einer Gemini KI-Recherche oder Analyse.
    """
    __tablename__ = "ai_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    podcast_id = Column(String(36), ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=True, index=True)
    episode_id = Column(String(36), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # 'wikitext_table', 'guests_topics', 'qa', 'custom_chat', 'summary'
    prompt = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    response_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Beziehungen
    podcast = relationship("Podcast", back_populates="ai_analyses")
    episode = relationship("Episode", back_populates="ai_analyses")
