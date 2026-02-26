from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ========== Token Schemas ==========
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None

# ========== User Schemas ==========
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr
    project_count: int
    created_at: datetime
    avatar_url: Optional[str] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class ThemeResponse(BaseModel):
    """用户主题偏好"""
    preset_id: str = "coffee"
    custom_color: Optional[str] = None


class ThemeUpdate(BaseModel):
    preset_id: Optional[str] = None
    custom_color: Optional[str] = None


# ========== AI Memory Schemas ==========
class Character(BaseModel):
    name: str
    description: str
    personality: Optional[str] = None
    background: Optional[str] = None
    goals: Optional[str] = None

class AIMemoryBase(BaseModel):
    outline: List[Dict[str, Any]] = []
    storyline: Optional[str] = None
    characters: List[Character] = []
    world_building: Dict[str, Any] = {}
    writing_style: Optional[str] = None
    key_points: List[str] = []
    notes: Optional[str] = None

class AIMemoryUpdate(BaseModel):
    outline: Optional[List[Dict[str, Any]]] = None
    storyline: Optional[str] = None
    characters: Optional[List[Character]] = None
    world_building: Optional[Dict[str, Any]] = None
    writing_style: Optional[str] = None
    key_points: Optional[List[str]] = None
    notes: Optional[str] = None

class AIMemoryResponse(AIMemoryBase):
    id: int
    project_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ========== Document Schemas ==========
class Block(BaseModel):
    id: str
    type: str  # 'paragraph', 'heading', 'list', 'quote', etc.
    content: str
    props: Optional[Dict[str, Any]] = {}

class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: List[Block] = []

class DocumentCreate(DocumentBase):
    parent_id: Optional[int] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[List[Block]] = None

class DocumentResponse(DocumentBase):
    id: int
    project_id: int
    parent_id: Optional[int]
    order_index: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ========== Project Schemas ==========
class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentResponse] = []
    ai_memory: Optional[AIMemoryResponse] = None
    
    class Config:
        from_attributes = True

# ========== AI Interaction Schemas ==========
class AIRequest(BaseModel):
    document_id: int
    action: str  # 'guide', 'revise', 'polish', 'continue', 'brainstorm'
    selected_text: Optional[str] = None
    instruction: Optional[str] = None

class AIStreamResponse(BaseModel):
    content: str
    done: bool = False

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str

class AIChatRequest(BaseModel):
    document_id: int
    messages: List[ChatMessage]
    include_memory: bool = True


class AIGenerateFromMemoryRequest(BaseModel):
    """根据项目设定 AI 生成请求"""
    project_id: int
    document_id: Optional[int] = None  # 可选，续写时传入当前文档 id
    generate_type: str = "opening"  # opening | continue | outline_section | scene | custom
    custom_instruction: Optional[str] = None  # generate_type=custom 时使用
    current_content: Optional[str] = None  # 续写时传入当前文档末尾内容

# ========== Template Schemas ==========
class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category: str = "novel"
    icon: str = "📝"
    outline: List[Dict[str, Any]] = []
    storyline: Optional[str] = None
    characters: List[Character] = []
    world_building: Dict[str, Any] = {}
    writing_style: Optional[str] = None

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    icon: str
    outline: List[Dict[str, Any]]
    storyline: Optional[str]
    characters: List[Character]
    world_building: Dict[str, Any]
    writing_style: Optional[str]
    is_system: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Document Version Schemas ==========
class DocumentVersionCreate(BaseModel):
    title: str
    content: List[Block]
    change_summary: Optional[str] = None

class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    title: str
    version_number: int
    change_summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
