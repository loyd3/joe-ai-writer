from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
import uuid

from app.database import get_db
from app.schemas.schemas import (
    UserCreate, UserResponse, Token, UserProfile, ThemeResponse, ThemeUpdate,
    ProfileUpdate, PasswordChange
)
from app.core.auth import (
    authenticate_user, create_access_token, create_user,
    get_user_by_username, get_user_by_email, get_user_by_id, decode_token,
    get_password_hash, verify_password
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# OAuth2 方案（auto_error=False 允许可选认证）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
oauth2_scheme_required = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme_required),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return {"id": user.id, "username": user.username, "email": user.email}

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """获取当前用户（可选）- 未登录返回 None 不报错"""
    if not token:
        return None
    try:
        token_data = decode_token(token)
        if token_data is None or token_data.user_id is None:
            return None
        
        user = get_user_by_id(db, token_data.user_id)
        if user is None or not user.is_active:
            return None
        
        return {"id": user.id, "username": user.username, "email": user.email}
    except Exception:
        return None

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建用户
    user = create_user(db, user_data.username, user_data.email, user_data.password)
    return user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout():
    """用户退出（前端清除 token 即可）"""
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前登录用户信息"""
    user = get_user_by_id(db, current_user["id"])
    return user

@router.get("/profile", response_model=UserProfile)
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户详细资料"""
    user = get_user_by_id(db, current_user["id"])
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "project_count": len(user.projects),
        "created_at": user.created_at,
        "avatar_url": getattr(user, "avatar_url", None),
    }


@router.put("/profile", response_model=UserProfile)
def update_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户资料（用户名、邮箱、头像 URL）"""
    user = get_user_by_id(db, current_user["id"])
    if body.username is not None:
        existing = get_user_by_username(db, body.username)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Username already registered")
        user.username = body.username
    if body.email is not None:
        existing = get_user_by_email(db, body.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = body.email
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "project_count": len(user.projects),
        "created_at": user.created_at,
        "avatar_url": getattr(user, "avatar_url", None),
    }


@router.put("/password")
def change_password(
    body: PasswordChange,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    user = get_user_by_id(db, current_user["id"])
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"message": "Password updated"}


# 头像上传目录（与 main 中 mount 的 static 对应）
AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "avatars")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.put("/avatar", response_model=UserProfile)
def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传头像（覆盖式），返回更新后的 profile"""
    user = get_user_by_id(db, current_user["id"])
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Allowed formats: jpg, png, gif, webp")
    os.makedirs(AVATAR_DIR, exist_ok=True)
    # 固定文件名便于覆盖，避免旧文件堆积
    filename = f"{user.id}{ext}"
    path = os.path.join(AVATAR_DIR, filename)
    try:
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()
    avatar_url = f"/static/avatars/{filename}"
    user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "project_count": len(user.projects),
        "created_at": user.created_at,
        "avatar_url": user.avatar_url,
    }


@router.get("/theme", response_model=ThemeResponse)
def get_theme(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户主题设置"""
    user = get_user_by_id(db, current_user["id"])
    return ThemeResponse(
        preset_id=user.theme_preset or "coffee",
        custom_color=user.theme_custom_color
    )


@router.put("/theme", response_model=ThemeResponse)
def update_theme(
    body: ThemeUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存当前用户主题设置"""
    user = get_user_by_id(db, current_user["id"])
    if body.preset_id is not None:
        user.theme_preset = body.preset_id
    if body.custom_color is not None:
        user.theme_custom_color = body.custom_color
    db.commit()
    db.refresh(user)
    return ThemeResponse(
        preset_id=user.theme_preset or "coffee",
        custom_color=user.theme_custom_color
    )
