from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Isolated settings: no .env file, no API keys, storage under tmp_path."""
    return Settings(
        _env_file=None,
        groq_api_key="",
        upload_dir=str(tmp_path / "uploads"),
        chroma_persist_dir=str(tmp_path / "chroma"),
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
