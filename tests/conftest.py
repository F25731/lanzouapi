from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine
from app.db.session import reset_session_factory
from app.db.session import session_scope
from app.main import create_app
from app.models.entities import File
from app.models.entities import SourceSource
from app.models.enums import FileStatus
from app.models.enums import SourceStatus
from app.utils.files import extract_extension
from app.utils.files import normalize_name
from app.utils.serialization import dumps_json


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)

    get_settings.cache_clear()
    reset_session_factory()
    Base.metadata.create_all(bind=get_engine())

    app = create_app()
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        reset_session_factory()
        get_settings.cache_clear()


@pytest.fixture
def seed_mock_file():
    def _seed(
        file_name: str = "book.epub",
        direct_url: str = "https://cdn.example.com/book.epub",
        hot_score: int = 0,
    ) -> int:
        with session_scope() as db:
            source = SourceSource(
                name="mock-source",
                adapter_type="mock",
                base_url=None,
                username="demo",
                password="demo",
                root_folder_id="root",
                config_json=dumps_json(
                    {
                        "folders": {
                            "root": {
                                "folders": [],
                                "files": [
                                    {
                                        "id": "remote-file-1",
                                        "name": file_name,
                                        "path": f"/{file_name}",
                                        "size_bytes": 1024,
                                        "share_url": "https://share.example.com/book",
                                    }
                                ],
                            }
                        },
                        "direct_links": {
                            "remote-file-1": direct_url,
                        },
                    }
                ),
                status=SourceStatus.ACTIVE,
                is_enabled=True,
                rate_limit_per_minute=60,
                request_timeout_seconds=10,
            )
            db.add(source)
            db.flush()

            file_record = File(
                source_id=source.id,
                provider_file_id="remote-file-1",
                file_name=file_name,
                normalized_name=normalize_name(file_name),
                file_path=f"/{file_name}",
                extension=extract_extension(file_name),
                size_bytes=1024,
                share_url="https://share.example.com/book",
                status=FileStatus.ACTIVE,
                hot_score=hot_score,
            )
            db.add(file_record)
            db.flush()
            return file_record.id

    return _seed
