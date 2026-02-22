# Joe AI Writer - 智能写作助手

类似 Notion 的 AI 辅助写作工具，支持 AI 指导、修改、润色，具备强大的记忆功能。

## 功能特性

- ✍️ 块级编辑器（类似 Notion）
- 🤖 AI 写作指导、修改、润色
- 🧠 AI 记忆系统：记住大纲、故事线、角色设定
- 📚 项目管理：多文档、多版本
- 🔌 数据库支持

## 技术栈

- **后端**: Python + FastAPI + SQLAlchemy
- **前端**: Vue3 + Element Plus + TipTap 编辑器
- **AI**: OpenAI API / 本地模型支持
- **数据库**: SQLite (开发) / PostgreSQL (生产)

## 项目结构

```
joe-ai-writer/
├── backend/           # Python FastAPI 后端
│   ├── app/
│   │   ├── api/       # API 路由
│   │   ├── core/      # 配置、AI 客户端
│   │   ├── models/    # 数据库模型
│   │   ├── schemas/   # Pydantic 模型
│   │   └── services/  # 业务逻辑
│   ├── migrations/    # 数据库迁移
│   └── requirements.txt
├── frontend/          # Vue3 前端
│   ├── src/
│   │   ├── components/# 组件
│   │   ├── views/     # 页面
│   │   ├── stores/    # Pinia 状态管理
│   │   └── api/       # API 客户端
│   └── package.json
└── docker-compose.yml # 可选：Docker 部署
```

## 快速开始

### 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

## AI 记忆系统

AI 会记住以下信息：
- 📋 文章大纲（Outline）
- 📖 故事线（Storyline）
- 👤 角色设定（Characters）
- 🌍 世界观（World Building）
- 📝 写作风格偏好

这些信息会被结构化存储，每次 AI 交互时自动注入上下文。
