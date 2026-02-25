"""默认用户逻辑：在无登录场景下保证 projects.owner_id 有合法外键"""
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_USER_EMAIL = "default@local"
DEFAULT_USER_USERNAME = "default"


def get_or_create_default_user(db: Session) -> User:
    """获取或创建默认用户（id=1），用于未接入真实用户系统时创建项目。"""
    user = db.query(User).filter(User.id == 1).first()
    if user:
        return user
    user = db.query(User).filter(User.email == DEFAULT_USER_EMAIL).first()
    if user:
        return user
    # 创建默认用户，密码占位
    user = User(
        email=DEFAULT_USER_EMAIL,
        username=DEFAULT_USER_USERNAME,
        hashed_password=pwd_context.hash("default"),
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except Exception:
        # 并发或唯一约束冲突时重新查询
        db.rollback()
        user = db.query(User).filter(User.email == DEFAULT_USER_EMAIL).first()
        if not user:
            raise
        return user
    return user
