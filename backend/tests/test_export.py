"""导出回归测试：结构化设定和项目显示顺序。"""
import asyncio
import os
import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import export
from app.api.auth import get_current_user
from app.database import Base, get_db
from app.models.models import AIMemory, Document, Project


@pytest.fixture
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(id=1, title="测试项目", owner_id=1)
        session.add(project)
        session.add(Document(id=1, project_id=1, title="测试文档", content=[
            {"type": "paragraph", "content": "正文内容"}]))
        session.commit()
        yield session
    engine.dispose()


def add_memory(db, legacy=False):
    memory = AIMemory(
        project_id=1, outline=[{"title": "开篇", "description": "开篇描述"}],
        storyline="旧故事线" if legacy else {
            "summary": "故事总览", "stages": [{"title": "起点", "summary": "踏上旅途"}]},
        characters=[{"name": "主角", "description": "勇敢", "background": "故乡"}],
        world_building={"时代": "古代"} if legacy else {
            "categories": [{"name": "地理", "items": [{"title": "城池", "content": "山中城"}]}]},
        key_points=["旧情节点"] if legacy else [{"title": "转折", "summary": "发现真相"}],
        writing_style="简洁", notes="不要遗漏备注")
    db.add(memory)
    db.commit()


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("target", ["document", "project", "docx"])
def test_export_with_memory(db, legacy, target):
    add_memory(db, legacy)
    project = db.get(Project, 1)
    document = db.get(Document, 1)
    if target == "document":
        result = export.generate_markdown(db, document, project, True)
    elif target == "project":
        result = export.generate_project_markdown(db, project, True)
    else:
        if not export.DOCX_AVAILABLE:
            pytest.skip("python-docx not installed")
        response = asyncio.run(export.export_docx(1, True, db, {"id": 1}))
        try:
            result = "\n".join(p.text for p in export.DocxDocument(response.path).paragraphs)
        finally:
            os.unlink(response.path)
    expected = ["开篇", "开篇描述", "主角", "故乡", "简洁", "不要遗漏备注", "正文内容"]
    expected += ["旧故事线", "古代", "旧情节点"] if legacy else [
        "故事总览", "起点", "踏上旅途", "地理", "城池", "山中城", "转折", "发现真相"]
    for value in expected:
        assert value in result
    assert "{'summary':" not in result
    assert "{'categories':" not in result


def test_project_order_matches_project_list(db):
    db.add_all([
        Document(id=2, project_id=1, title="第二篇", order_index=0, content=[]),
        Document(id=3, project_id=1, title="优先篇", order_index=-1, content=[]),
        Document(id=4, project_id=1, title="末篇", order_index=5, content=[]),
    ])
    db.commit()
    # 同排序值的行不可依赖数据库自然顺序；此索引会使未指定 id 的查询倒序返回。
    db.execute(text("CREATE INDEX export_order_test ON documents(order_index, id DESC)"))
    project = db.get(Project, 1)
    result = export.generate_project_markdown(db, project, False)
    titles = ["优先篇", "测试文档", "第二篇", "末篇"]
    positions = [result.index(title) for title in titles]
    assert positions == sorted(positions)
    payload = export.build_project_export_payload(db, project, False)
    assert [d["title"] for d in payload["documents"]] == titles


@pytest.mark.parametrize("include_memory", [True, False])
@pytest.mark.parametrize("path", ["document/1/markdown", "project/1/markdown", "project/1/json"])
def test_export_download_endpoints(db, include_memory, path):
    add_memory(db)
    app = FastAPI()
    app.include_router(export.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1}
    async def download():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(f"/api/export/{path}", params={"include_memory": include_memory})

    response = asyncio.run(download())
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert ("故事总览" in response.text) is include_memory


def test_empty_memory_placeholders(db):
    memory = AIMemory(
        project_id=1, storyline={"summary": "", "stages": []},
        characters=[{}], world_building={"categories": [{"name": "地理", "items": []}]})
    db.add(memory)
    db.commit()
    assert not export.has_memory_content(memory)


def test_notes_only_memory(db):
    memory = AIMemory(project_id=1, notes="唯一设定")
    db.add(memory)
    db.commit()
    assert export.has_memory_content(memory)
    result = export.generate_markdown(db, db.get(Document, 1), db.get(Project, 1), True)
    assert "唯一设定" in result
