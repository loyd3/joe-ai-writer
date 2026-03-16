from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import os
from app.database import engine, Base
from app.api import projects, ai, auth, search, export, templates, versions, extract, system, dashboard, hot_topics, publish, ai_story_generator, long_article, import_project, brainstorm
from sqlalchemy import text

# 创建数据库表
Base.metadata.create_all(bind=engine)


def _ensure_avatar_column():
    """若 users 表缺少 avatar_url 列则自动添加，避免登录 500"""
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) DEFAULT NULL"))
            conn.commit()
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "already exists" in msg or "1060" in msg or "exist" in msg:
            pass  # 列已存在，忽略
        else:
            raise

# 静态文件目录（头像等）
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(static_dir, "avatars"), exist_ok=True)

app = FastAPI(
    title="墨心 API（AI 辅助写作）",
    description="AI-powered writing assistant with memory",
    version="2.0.0"
)


@app.on_event("startup")
def startup():
    try:
        _ensure_avatar_column()
    except Exception:
        pass  # 非致命，仅个人中心头像功能受影响

# 允许的前端来源
_frontend_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:8080",  # Docker 运行端口
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",  # Docker 运行端口
]


def _add_cors_to_response(response, origin: str | None):
    if origin and origin in _frontend_origins:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Access-Control-Allow-Credentials", "true")


class EnsureCORSHeadersMiddleware(BaseHTTPMiddleware):
    """确保所有响应（含 500 等异常）都带上 CORS 头"""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        try:
            response = await call_next(request)
            _add_cors_to_response(response, origin)
            return response
        except Exception as e:
            resp = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error": str(e)},
            )
            _add_cors_to_response(resp, origin)
            return resp


app.add_middleware(EnsureCORSHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(import_project.router)
app.include_router(templates.router)
app.include_router(versions.router)
app.include_router(extract.router)
app.include_router(system.router)
# app.include_router(rag.router)  # RAG 功能已移除
app.include_router(dashboard.router)
app.include_router(hot_topics.router)
app.include_router(brainstorm.router)
app.include_router(publish.router)
app.include_router(ai_story_generator.router)
app.include_router(long_article.router)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def root():
    return {"message": "墨心 API · AI 辅助写作", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
