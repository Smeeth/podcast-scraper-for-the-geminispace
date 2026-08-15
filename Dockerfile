# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

FROM python:3.11-slim

# Umgebungsvariablen für optimierte Python-Ausführung
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# System-Abhängigkeiten installieren (ffmpeg für yt-dlp, curl für Healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Unprivilegierten Non-Root-Benutzer anlegen (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Python-Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungsdateien kopieren und Berechtigungen setzen
COPY . .
RUN chown -R appuser:appgroup /app

# Zum Non-Root User wechseln
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
