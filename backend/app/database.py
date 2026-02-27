import time
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError, DatabaseError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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
        "pool_timeout": 30,  # 获取连接超时时间
    }

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **pool_kwargs
)

# 监听连接事件，记录连接问题
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接检出时的处理"""
    try:
        # 测试连接是否有效
        dbapi_conn.cursor().execute("SELECT 1")
    except Exception as e:
        logger.warning(f"Stale connection detected, will be recycled: {e}")
        raise OperationalError("Connection is stale", None, e)

@event.listens_for(engine, "close")
def on_close(dbapi_conn, connection_record):
    logger.debug("Database connection closed")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db(max_retries: int = 3, retry_delay: float = 1.0):
    """
    获取数据库会话，带重试机制
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    """
    last_exception = None
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            # 测试连接
            db.execute(text("SELECT 1"))
            yield db
            return
        except OperationalError as e:
            last_exception = e
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            db.close()
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            db.rollback()
            raise
        finally:
            if db:
                db.close()
    
    # 所有重试都失败
    logger.error(f"Failed to get database connection after {max_retries} attempts")
    raise last_exception or DatabaseError("Unable to connect to database")


def get_db_with_fallback(max_retries: int = 3):
    """
    获取数据库会话的同步版本（用于非生成器场景）
    """
    last_exception = None
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return db
        except OperationalError as e:
            last_exception = e
            logger.warning(f"DB connection attempt {attempt + 1}/{max_retries} failed")
            db.close()
            if attempt < max_retries - 1:
                time.sleep(1.0)
        except Exception:
            db.close()
            raise
    
    raise last_exception or DatabaseError("Unable to connect to database")


def init_database():
    """
    初始化数据库 - 创建所有表
    用于 Docker 容器启动时自动初始化
    """
    from app.models.models import Base as ModelsBase
    
    logger.info("Initializing database...")
    try:
        # 导入所有模型以确保它们被注册
        import app.models.models
        
        # 创建所有表
        ModelsBase.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
