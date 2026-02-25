# API 文档

## 基础信息

- 基础 URL: `http://localhost:8000/api`
- 文档地址: `http://localhost:8000/docs` (Swagger UI)

## 项目 API

### 获取项目列表
```http
GET /projects
```

**响应**
```json
[
  {
    "id": 1,
    "title": "我的小说",
    "description": "科幻小说",
    "created_at": "2024-01-20T10:00:00",
    "updated_at": "2024-01-20T12:00:00"
  }
]
```

### 创建项目
```http
POST /projects
Content-Type: application/json

{
  "title": "新项目",
  "description": "可选描述"
}
```

### 获取项目详情
```http
GET /projects/{id}
```

### 更新项目
```http
PUT /projects/{id}
Content-Type: application/json

{
  "title": "新标题",
  "description": "新描述"
}
```

### 删除项目
```http
DELETE /projects/{id}
```

---

## 文档 API

### 获取项目下的文档
```http
GET /projects/{project_id}/documents
```

### 创建文档
```http
POST /projects/{project_id}/documents
Content-Type: application/json

{
  "title": "第一章",
  "content": [
    {
      "id": "block-1",
      "type": "paragraph",
      "content": "这是内容",
      "props": {}
    }
  ],
  "parent_id": null
}
```

### 获取文档
```http
GET /documents/{id}
```

### 更新文档
```http
PUT /documents/{id}
Content-Type: application/json

{
  "title": "新标题",
  "content": [...]
}
```

### 删除文档
```http
DELETE /documents/{id}
```

---

## 项目设定 API

### 获取项目记忆
```http
GET /projects/{project_id}/memory
```

**响应**
```json
{
  "id": 1,
  "project_id": 1,
  "outline": [
    {"title": "第一章：开端"},
    {"title": "第二章：发展"}
  ],
  "storyline": "故事概述...",
  "characters": [
    {
      "name": "主角",
      "description": "一个勇敢的人",
      "personality": "乐观、坚韧",
      "goals": "拯救世界"
    }
  ],
  "world_building": {
    "时代": "未来",
    "地点": "火星"
  },
  "writing_style": "简洁明快",
  "key_points": ["关键情节1", "关键情节2"],
  "notes": "其他备注"
}
```

### 更新记忆
```http
PUT /projects/{project_id}/memory
Content-Type: application/json

{
  "outline": [{"title": "新章节"}],
  "storyline": "新的故事线",
  "characters": [...],
  "world_building": {...},
  "writing_style": "新的风格",
  "key_points": [...],
  "notes": "新备注"
}
```

---

## AI 写作 API

### AI 辅助（非流式）
```http
POST /ai/assist
Content-Type: application/json

{
  "document_id": 1,
  "action": "guide",
  "selected_text": "选中的文本",
  "instruction": "具体要求"
}
```

**action 类型**
- `guide` - 写作指导
- `revise` - 修改文本
- `polish` - 润色
- `continue` - 续写
- `brainstorm` - 头脑风暴
- `expand` - 扩展细节
- `summarize` - 总结

### AI 辅助（流式）
```http
POST /ai/assist/stream
Content-Type: application/json

{
  "document_id": 1,
  "action": "guide",
  "selected_text": "...",
  "instruction": "..."
}
```

**响应格式** (Server-Sent Events)
```
data: 第一个字

data: 第二个字

data: [DONE]
```

### AI 对话（流式）
```http
POST /ai/chat/stream
Content-Type: application/json

{
  "document_id": 1,
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！"}
  ],
  "include_memory": true
}
```

---

## 数据模型

### Block 块
```typescript
{
  id: string;           // 唯一标识
  type: string;         // 'paragraph' | 'heading' | 'quote' | 'list'
  content: string;      // 文本内容
  props: Record<string, any>;  // 额外属性
}
```

### Character 角色
```typescript
{
  name: string;         // 角色名
  description: string;  // 描述
  personality?: string; // 性格
  background?: string;  // 背景
  goals?: string;       // 目标
}
```