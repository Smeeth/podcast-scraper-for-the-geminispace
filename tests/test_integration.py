# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Podcast & Media Channel Researcher Contributors

import asyncio
import unittest

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app


class TestFastAPIIntegration(unittest.TestCase):
    """Integrationstests für die FastAPI Endpunkte."""

    @classmethod
    def setUpClass(cls):
        # In-Memory SQLite für isolierte, reproduzierbare Integrationstests
        cls.test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        cls.async_session_factory = async_sessionmaker(
            bind=cls.test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

        async def init_tables():
            async with cls.test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(init_tables())

        async def override_get_db():
            async with cls.async_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("database", data)
        self.assertIn("gemini_available", data)

    def test_security_headers_present(self):
        resp = self.client.get("/api/health")
        headers = resp.headers
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertEqual(headers.get("referrer-policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_static_index_html_served(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Media Researcher & AI Analyzer", resp.text)
        self.assertIn('data-bs-theme="dark"', resp.text)

    def test_ssrf_blocked_on_scrape_endpoint(self):
        resp = self.client.post("/api/scrape", json={"url": "http://169.254.169.254/latest/meta-data/"})
        self.assertEqual(resp.status_code, 422)  # Pydantic validation error

    def test_ssrf_dword_blocked_on_scrape_endpoint(self):
        resp = self.client.post("/api/scrape", json={"url": "http://2130706433/admin"})
        self.assertEqual(resp.status_code, 422)

    def test_probe_endpoint_ssrf_blocked(self):
        resp = self.client.post("/api/probe", json={"url": "http://127.0.0.1:8000/feed"})
        self.assertEqual(resp.status_code, 422)

    def test_podcasts_list_empty(self):
        resp = self.client.get("/api/podcasts")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_search_transcripts_endpoint_empty(self):
        resp = self.client.get("/api/search/transcripts?q=OpenSource")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["query"], "OpenSource")
        self.assertEqual(data["total_matches"], 0)
        self.assertIsInstance(data["results"], list)

    def test_export_endpoint_validation(self):
        # Ungültiges Format
        resp = self.client.get("/api/export/non-existent-id?format=invalid_fmt")
        self.assertEqual(resp.status_code, 422)

        # Gültige Exportformate (geben 404 für nicht existierenden Podcast, aber kein 422)
        valid_formats = ["json", "csv", "markdown", "wikitext", "wikipedia_template", "gemtext", "gopher"]
        for fmt in valid_formats:
            resp = self.client.get(f"/api/export/non-existent-id?format={fmt}")
            self.assertEqual(resp.status_code, 404, f"Format {fmt} sollte akzeptiert werden (404 statt 422)")

    def test_ai_analysis_validation(self):
        # Nicht existierender Podcast
        resp = self.client.post("/api/ai/analyze", json={
            "podcast_id": "non-existent-id",
            "analysis_type": "wikitext_table",
            "style_format": "template"
        })
        self.assertEqual(resp.status_code, 404)

    def test_publish_endpoint(self):
        resp = self.client.post("/api/publish")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("gemini_files_count", data)
        self.assertIn("gopher_files_count", data)

    def test_publish_status_endpoint(self):
        resp = self.client.get("/api/publish/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("gemini_directory", data)
        self.assertIn("gopher_directory", data)


if __name__ == "__main__":
    unittest.main()

