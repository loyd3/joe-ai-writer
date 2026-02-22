from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# ========== User Schemas ==========
class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

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
    title: str
    content: List[Block] = []

class DocumentCreate(DocumentBase):
    parent_id: Optional[int] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
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
    title: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

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