from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
import logging
import os
import time
from app.database import engine, Base
from app.api import projects, ai, auth, search, export, templates, versions, extract, system, dashboard, hot_topics, publish, ai_story_generator, long_article, import_project, brainstorm, auto_write
from app.api import hot_topics_compat, brainstorm_compat
from app.api import copywriting_compat
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _init_database(max_retries: int = 10, delay: float = 2.0) -> bool:
    """创建表结构；数据库未就绪时重试，避免启动直接崩溃。"""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return True
        except Exception as e:
            last_err = e
            logger.warning(
                "数据库初始化失败 (%s/%s): %s",
                attempt,
                max_retries,
                e,
            )
            if attempt < max_retries:
                time.sleep(delay)
    logger.error("数据库初始化最终失败: %s", last_err)
    return False


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
    if not _init_database():
        logger.error(
            "无法连接数据库，请检查 DATABASE_URL；"
            "若使用 Docker MySQL：docker compose up -d mysql，并确认端口 3307"
        )
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
app.include_router(hot_topics_compat.router)
app.include_router(brainstorm_compat.router)
app.include_router(copywriting_compat.router)
app.include_router(publish.router)
app.include_router(ai_story_generator.router)
app.include_router(long_article.router)
app.include_router(auto_write.router)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def root():
    return {"message": "墨心 API · AI 辅助写作", "version": "2.0.0"}

@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def auth_compat_redirect(path: str):
    """
    兼容旧地址：/auth/* -> /api/auth/*
    使用 307 以保留方法（尤其是 POST /auth/login）。
    """
    return RedirectResponse(url=f"/api/auth/{path}", status_code=307)

@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok"}
