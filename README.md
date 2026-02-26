# 📝 墨心

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 一款支持多模型 AI 和完整故事管理的智能写作助手。

---

## ✨ 功能特性

### 🤖 多模型 AI 支持
- **OpenAI** - GPT-4, GPT-3.5-turbo 等系列
- **DeepSeek** - deepseek-chat, deepseek-coder, deepseek-reasoner
- **SiliconFlow** - DeepSeek-V3, Qwen, Llama 等多种开源模型
- **自定义 API** - 支持任何兼容 OpenAI API 格式的端点
- **实时切换** - 无需重启即可在设置中切换模型

### 🧠 项目设定系统
- **项目级记忆** - 每个项目独立记忆空间
- **结构化存储** - 大纲、角色、故事线、世界观分类管理
- **事件设定** - 管理故事中的关键事件，支持时间线排序
- **智能上下文注入** - 自动在 AI 对话中引用记忆

### ✍️ 编辑器
- **块级编辑** - 类似 Notion 的流畅体验
- **快捷键支持** - `/` 快速命令、`Ctrl+Enter` 发送
- **实时保存** - 自动保存到数据库
- **AI 辅助** - 润色、续写、改写、头脑风暴

### 📊 故事管理
| 功能 | 说明 |
|------|------|
| 大纲 | 定义文章整体结构 |
| 角色设定 | 管理人物属性、关系 |
| 事件设定 | 追踪关键情节节点 |
| 故事线 | 梳理情节发展脉络 |
| 世界观 | 设定背景规则 |

---

## 🚀 快速开始

### 前置要求

1. **MySQL 数据库**（默认使用本地 MySQL）
   ```bash
   # macOS
   brew install mysql
   brew services start mysql
   
   # Ubuntu/Debian
   sudo apt-get install mysql-server
   sudo systemctl start mysql
   
   # 创建数据库
   mysql -u root -p
   CREATE DATABASE joe_writer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Node.js** (v20+) 和 **Python** (v3.11+)

### 方式一：一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-writer.git
cd joe-ai-writer

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key 和数据库连接

# 初始化数据库（自动创建表）
python init_db.py

# 一键启动（自动安装依赖）
python start.py
```

访问 http://localhost:5173

### 方式二：手动启动

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置 API Key
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

### 方式三：Docker 部署

```bash
# 配置环境变量
export OPENAI_API_KEY=your-key

# 启动全部服务
docker-compose up -d
```

---

## 📁 项目结构

```
joe-ai-writer/
├── start.py              # 一键启动脚本
├── init_db.py            # 数据库初始化脚本
├── .env.example          # 环境变量模板
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   │   ├── ai.py           # AI 写作接口
│   │   │   ├── events.py       # 事件管理接口
│   │   │   ├── projects.py     # 项目/文档接口
│   │   │   └── system.py       # 系统配置接口
│   │   ├── core/
│   │   │   ├── ai_client.py    # 多模型 AI 客户端
│   │   │   └── config.py       # 配置管理
│   │   ├── models/      # 数据库模型
│   │   └── services/    # 业务逻辑
│   ├── database/
│   │   └── init.sql     # 数据库建表 SQL
│   └── requirements.txt
├── frontend/            # Vue3 前端
│   └── src/
│       ├── components/
│       │   ├── ProjectSettingsManager.vue   # 项目设定管理
│       │   ├── AIConfigPanel.vue     # AI 配置面板
│       │   ├── EventManager.vue      # 事件管理
│       │   ├── BlockEditor.vue       # 块级编辑器
│       │   └── AIChatPanel.vue       # AI 对话面板
│       ├── stores/      # Pinia 状态管理
│       └── views/       # 页面视图
└── docs/                # 文档
```

---

## 🔧 配置说明

### 数据库配置

默认使用 **MySQL**，支持自动连接池管理。

```bash
# MySQL 配置（默认）
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/aiwriter?charset=utf8mb4

# 连接池配置
DB_POOL_SIZE=5          # 连接池大小
DB_MAX_OVERFLOW=10      # 最大溢出连接
DB_POOL_RECYCLE=3600    # 连接回收时间（秒）
```

如果需要使用 SQLite（仅用于测试）：
```bash
DATABASE_URL=sqlite:///./aiwriter.db
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商: `openai`, `deepseek`, `siliconflow`, `custom` | `deepseek` |
| `DATABASE_URL` | 数据库连接 | MySQL 连接字符串 |
| `AI_TEMPERATURE` | AI 创造性参数 | `0.7` |
| `AI_MAX_TOKENS` | 最大生成长度 | `4096` |

### 各模型配置

```bash
# OpenAI
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4

# DeepSeek
DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-chat

# SiliconFlow
SILICONFLOW_API_KEY=your-key
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V3

# 自定义
CUSTOM_API_KEY=your-key
CUSTOM_BASE_URL=https://your-api.com/v1
CUSTOM_MODEL=your-model
```

---

## 🛠️ 技术栈

**后端**
- FastAPI - 高性能 Python Web 框架
- SQLAlchemy - ORM 数据库操作
- OpenAI SDK - 多模型 AI 统一接口
- Pydantic - 数据验证

**前端**
- Vue 3 + TypeScript
- Element Plus - UI 组件库
- Pinia - 状态管理
- Axios - HTTP 客户端

---

## 📝 更新日志

### v1.2.0 (2024-02)
- ✅ MySQL 数据库支持（默认）
- ✅ 数据库连接池管理
- ✅ 数据库初始化脚本

### v1.1.0 (2024-02)
- ✅ 多模型 AI 支持（OpenAI, DeepSeek, SiliconFlow）
- ✅ 事件设定管理功能
- ✅ 一键启动脚本
- ✅ AI 配置面板
- ✅ 系统健康检查接口

### v1.0.0 (2024-01)
- ✅ 基础编辑器
- ✅ 项目设定系统
- ✅ 流式 AI 响应
- ✅ 项目/文档管理

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

1. Fork 本仓库
2. 创建分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add feature'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 创建 Pull Request

---

## 📄 许可证

[MIT License](./LICENSE)

---

<p align="center">Made with ❤️ by <a href="https://github.com/loyd3">loyd3</a></p>
