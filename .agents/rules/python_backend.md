<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Podcast & Media Channel Researcher Contributors -->

# Rule: Python Backend Guidelines

Guidelines for writing and maintaining Python code in this repository.

## Standards

1. **Python Version**: Target Python 3.11+.
2. **Type Annotations**: All functions, methods, and FastAPI routes must include type hints.
3. **Async / Await**:
   - Route handlers and database queries must be asynchronous (`async def`, `await session.execute(...)`).
   - Use `AsyncSession` from `app.database`.
4. **Pydantic Models**:
   - Define data contracts and request/response payloads in `app/schemas.py` using Pydantic v2.
   - Use `model_validate`, `model_dump()` instead of deprecated v1 methods.
5. **Linting & Formatting**:
   - Follow PEP 8 via Ruff (`ruff check` & `ruff format`).
   - Keep maximum line length within 100 characters where practical.
