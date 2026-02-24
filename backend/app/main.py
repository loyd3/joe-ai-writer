from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import projects, ai, system, events

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Joe AI Writer API",
    description="AI-powered writing assistant with memory - 支持多模型 AI",
    version="1.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
