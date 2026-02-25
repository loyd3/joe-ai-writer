from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import projects, ai, system, events
from app.core.config import get_settings

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Joe AI Writer API",
    description="AI-powered writing assistant with memory - 支持多模型 AI",
    version="1.1.0",
)

# CORS 配置：支持环境变量 CORS_ORIGINS（逗号分隔），否则使用默认开发列表
_settings = get_settings()
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://[::1]:5173",
    "http://[::1]:3000",
]
if _settings.cors_origins:
    allow_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
else:
    allow_origins = _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(system.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {
        "message": "Joe AI Writer API",
        "version": "1.1.0",
        "features": ["multi-provider-ai", "memory-system", "streaming", "event-tracking"],
    }
