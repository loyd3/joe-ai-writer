from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import projects, ai

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Joe AI Writer API",
    description="AI-powered writing assistant with memory",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vue 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(projects.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "Joe AI Writer API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}