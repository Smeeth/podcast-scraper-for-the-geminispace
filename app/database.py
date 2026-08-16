# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base-Klasse
class Base(DeclarativeBase):
    pass

# Async Engine mit Connection Pooling & Pre-Ping
engine_args: dict[str, Any] = {
    "echo": False,
    "future": True,
}

if "sqlite" in settings.DATABASE_URL:
    # Spezifische SQLite-Optionen (z.B. für lokale Tests)
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL Connection Pooling Optionen
    engine_args["pool_pre_ping"] = True
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **engine_args)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency zur Bereitstellung einer asynchronen SQLAlchemy Session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(max_retries: int = 10, retry_delay: float = 2.0) -> None:
    """
    Initialisiert die Datenbanktabellen mit resilienter Retry-Logik beim Container-Kaltstart.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Initialisiere Datenbankverbindung (Versuch {attempt}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Datenbanktabellen erfolgreich initialisiert.")
            return
        except Exception as e:
            logger.warning(f"Datenbank noch nicht bereit (Versuch {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                logger.error("Konnte keine Verbindung zur Datenbank aufbauen. Abbruch.")
                raise
            await asyncio.sleep(retry_delay)
