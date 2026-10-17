"""Optimistic document saves must not overwrite newer agent/editor content."""
import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.api import projects
from app.api.auth import get_current_user
from app.database import Base, get_db
from app.models.models import Document, Project


BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, 123456)


def blocks(text):
    return [{"id": "body", "type": "paragraph", "content": text, "props": {}}]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'documents.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Project(id=1, title="Owned project", owner_id=1),
            Project(id=2, title="Other project", owner_id=2),
        ])
        db.add_all([
            Document(id=1, project_id=1, title="Original", content=blocks("snapshot"), updated_at=BASE_TIME),
            Document(id=2, project_id=2, title="Private", content=blocks("private"), updated_at=BASE_TIME),
        ])
        db.commit()
        app = FastAPI()
        app.include_router(projects.router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        monkeypatch.setattr(projects, "_index_document_async", lambda *args: None)
        yield app, db, engine
    engine.dispose()


def save(app, document_id=1, **payload):
    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.put(f"/api/documents/{document_id}", json=payload)
    return asyncio.run(request())


def test_old_snapshot_after_agent_update_conflicts_without_writes(setup):
    app, db, engine = setup
    document = db.get(Document, 1)
    document.content = blocks("new agent text")
    document.updated_at = BASE_TIME + timedelta(seconds=1)
    db.commit()
    statements = []
    event.listen(engine, "before_cursor_execute", lambda conn, cursor, statement, params, context, many: statements.append(statement))

    response = save(app, title="stale title", content=blocks("stale editor text"), expected_updated_at=BASE_TIME.isoformat())

    assert response.status_code == 409
    db.expire_all()
    assert db.get(Document, 1).content == blocks("new agent text")
    assert db.get(Document, 1).title == "Original"
    assert not any(statement.lstrip().upper().startswith("INSERT") for statement in statements)


@pytest.mark.parametrize("offset", [None, timezone.utc, timezone(timedelta(hours=8))])
def test_valid_snapshot_succeeds_and_advances_version(setup, offset):
    app, db, _ = setup
    expected = BASE_TIME if offset is None else BASE_TIME.replace(tzinfo=timezone.utc).astimezone(offset)
    response = save(app, content=blocks("saved text"), expected_updated_at=expected.isoformat())
    assert response.status_code == 200
    assert response.json()["content"] == blocks("saved text")
    assert datetime.fromisoformat(response.json()["updated_at"]) > BASE_TIME
    assert save(app, content=blocks("reused snapshot"), expected_updated_at=expected.isoformat()).status_code == 409


def test_unrelated_owner_is_rejected_before_version_check(setup):
    app, db, _ = setup
    response = save(app, document_id=2, content=blocks("intrusion"), expected_updated_at=(BASE_TIME - timedelta(days=1)).isoformat())
    assert response.status_code == 403
    db.expire_all()
    assert db.get(Document, 2).content == blocks("private")


@pytest.mark.parametrize("guard", [{}, {"expected_updated_at": None}])
def test_legacy_or_null_guard_save_remains_compatible(setup, guard):
    app, db, _ = setup
    response = save(app, content=blocks("legacy text"), **guard)
    assert response.status_code == 200
    assert response.json()["content"] == blocks("legacy text")
    assert not hasattr(db.get(Document, 1), "expected_updated_at")


def test_update_between_access_check_and_write_is_atomic(setup, monkeypatch):
    app, db, engine = setup
    original_check = projects.check_project_owner

    def concurrent_agent_update(session, project_id, user_id):
        project = original_check(session, project_id, user_id)
        with Session(engine) as agent_db:
            agent_db.query(Document).filter(Document.id == 1).update({
                "content": blocks("concurrent agent text"),
                "updated_at": BASE_TIME + timedelta(seconds=1),
            })
            agent_db.commit()
        return project

    monkeypatch.setattr(projects, "check_project_owner", concurrent_agent_update)
    response = save(app, content=blocks("stale editor text"), expected_updated_at=BASE_TIME.isoformat())
    assert response.status_code == 409
    db.expire_all()
    assert db.get(Document, 1).content == blocks("concurrent agent text")


def test_guard_only_is_not_a_document_field_mutation(setup):
    app, db, _ = setup
    response = save(app, expected_updated_at=None)
    assert response.status_code == 200
    assert db.get(Document, 1).updated_at == BASE_TIME
    assert not hasattr(db.get(Document, 1), "expected_updated_at")


def test_same_clock_timestamp_still_advances_version(setup, monkeypatch):
    app, db, _ = setup
    # A future timestamp also models a clock adjustment / identical clock tick.
    future = datetime.utcnow() + timedelta(days=1)
    db.get(Document, 1).updated_at = future
    db.commit()
    response = save(app, content=blocks("changed"), expected_updated_at=future.isoformat())
    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["updated_at"]) > future
