from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import projects, ai, auth, search, export, templates, versions, extract, system, rag, dashboard

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="墨心 API（AI 辅助写作）",
    description="AI-powered writing assistant with memory",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(ai.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(versions.router)
app.include_router(extract.router)
app.include_router(system.router)
app.include_router(rag.router)
app.include_router(dashboard.router)

@app.get("/")
def root():
    return {"message": "墨心 API · AI 辅助写作", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
