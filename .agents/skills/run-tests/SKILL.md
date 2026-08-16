---
name: run-tests
description: >-
  Use this skill to run unit and integration tests for the Podcast Researcher repository,
  check test coverage, or troubleshoot test failures.
---

# Run Tests Skill

This skill explains how to execute the automated test suite for the Podcast & Media Channel Researcher.

## Procedures

### 1. Run All Tests

Execute pytest across the full test suite:

```bash
pytest tests -v
```

### 2. Run Specific Test Suites

- **Core Tests**:

  ```bash
  pytest tests/test_core.py -v
  ```

- **Integration Tests**:

  ```bash
  pytest tests/test_integration.py -v
  ```

### 3. Run with Coverage Report

To inspect test coverage across the `app` package:

```bash
pytest tests --cov=app --cov-report=term-missing
```

### 4. Troubleshooting

- If database errors occur, verify `DATABASE_URL` in `.env` or use the in-memory SQLite fallback (`sqlite+aiosqlite:///:memory:`).
- Verify virtual environment dependencies: `pip install -r requirements.txt`.
