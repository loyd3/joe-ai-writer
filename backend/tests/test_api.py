import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ========== 项目测试 ==========


def test_create_project(client):
    response = client.post("/api/projects", json={"title": "测试项目", "description": "测试描述"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试项目"
    assert data["description"] == "测试描述"
    assert "id" in data


def test_get_projects(client):
    # 先创建一个项目
    client.post("/api/projects", json={"title": "项目1"})
    client.post("/api/projects", json={"title": "项目2"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_update_project(client):
    # 创建
    create_res = client.post("/api/projects", json={"title": "原名称"})
    project_id = create_res.json()["id"]

    # 更新
    response = client.put(f"//api/projects/{project_id}", json={"title": "新名称"})
    assert response.status_code == 200
    assert response.json()["title"] == "新名称"


def test_delete_project(client):
    create_res = client.post("/api/projects", json={"title": "待删除"})
    project_id = create_res.json()["id"]

    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200

    # 确认已删除
    get_res = client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 404


# ========== 文档测试 ==========


def test_create_document(client):
    # 先创建项目
    project_res = client.post("/api/projects", json={"title": "测试项目"})
    project_id = project_res.json()["id"]

    response = client.post(
        f"/api/projects/{project_id}/documents", json={"title": "第一章", "content": []}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "第一章"
    assert data["project_id"] == project_id


def test_update_document(client):
    # 创建项目
    project_res = client.post("/api/projects", json={"title": "测试项目"})
    project_id = project_res.json()["id"]

    # 创建文档
    doc_res = client.post(
        f"/api/projects/{project_id}/documents", json={"title": "原标题", "content": []}
    )
    doc_id = doc_res.json()["id"]

    # 更新
    response = client.put(
        f"/api/documents/{doc_id}",
        json={"title": "新标题", "content": [{"id": "1", "type": "paragraph", "content": "内容"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新标题"
    assert len(data["content"]) == 1


# ========== AI 记忆测试 ==========


def test_get_memory(client):
    project_res = client.post("/api/projects", json={"title": "测试项目"})
    project_id = project_res.json()["id"]

    response = client.get(f"/api/projects/{project_id}/memory")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["outline"] == []


def test_update_memory(client):
    project_res = client.post("/api/projects", json={"title": "测试项目"})
    project_id = project_res.json()["id"]

    response = client.put(
        f"/api/projects/{project_id}/memory",
        json={
            "outline": [{"title": "第一章"}],
            "storyline": "故事线",
            "characters": [{"name": "主角", "description": "描述"}],
            "world_building": {"时代": "现代"},
            "writing_style": "简洁",
            "key_points": ["关键点1"],
            "notes": "备注",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["outline"]) == 1
    assert data["characters"][0]["name"] == "主角"
