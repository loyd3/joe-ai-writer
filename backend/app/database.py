from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

# 根据数据库类型设置连接参数
connect_args = {}
pool_kwargs = {}

if settings.database_url.startswith("sqlite"):
    # SQLite 配置
    connect_args = {"check_same_thread": False}
else:
    # MySQL/PostgreSQL 连接池配置
    pool_kwargs = {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_recycle": settings.db_pool_recycle,
        "pool_pre_ping": True,  # 自动检测断开的连接
    }

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
