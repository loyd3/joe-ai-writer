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

### 🔥 热点写作
| 功能 | 说明 |
|------|------|
| 热点抓取 | 自动抓取微博、知乎、百度、头条等平台热搜 |
| AI 大纲生成 | 根据热点自动生成文章结构和标题选项 |
| AI 文章写作 | 流式生成完整文章内容 |
| 一键保存 | 直接保存到项目，无缝衔接编辑 |

- **四步流程**: 选择热点 → 配置参数 → 生成大纲 → AI写作 → 保存文档

### 🤖 AI 故事生成器（v2.0 新增）
| 功能 | 说明 |
|------|------|
| 多种故事类型 | 支持玄幻、科幻、言情、悬疑、武侠、都市等多种类型 |
| 角色设定 | 自定义主角、配角、反派角色属性 |
| 世界观构建 | 设定故事背景、规则、势力分布 |
| 情节大纲 | AI 自动生成完整故事大纲 |
| 智能续写 | 根据已有内容智能续写故事 |

- **使用流程**: 选择类型 → 设定角色 → 构建世界观 → 生成大纲 → AI写作

### 📚 长篇文章生成器（v2.0 新增）
| 功能 | 说明 |
|------|------|
| 超长文章支持 | 支持生成 10万-100万字超长文章 |
| 智能分章节 | 自动规划章节结构，分批次生成 |
| 断点续写 | 支持暂停后继续生成，不怕中断 |
| 多种风格 | 专业学术、通俗科普、新闻报道、文学叙事等 |
| 大纲预览 | 生成前预览完整大纲，可调整修改 |

- **使用流程**: 设置主题 → 选择风格/字数 → 生成大纲 → 确认后生成 → 导出文档

### ✨ 自动写作（v2.0 新增）
| 功能 | 说明 |
|------|------|
| 热点自动抓取 | 自动获取最新热点话题 |
| 一键生成 | 输入主题即可自动生成完整文章 |
| 智能配图建议 | 根据内容推荐配图关键词 |
| 多平台适配 | 支持公众号、知乎、头条等平台风格 |
| 定时任务 | 支持设置定时自动生成任务 |

- **使用流程**: 输入主题/选择热点 → 配置参数 → 一键生成 → 编辑发布

### 💡 脑洞写作（v2.0 新增）
| 功能 | 说明 |
|------|------|
| 创意发散 | 基于关键词进行头脑风暴 |
| 随机灵感 | 随机生成创意写作灵感 |
| 故事接龙 | AI 与用户共同创作故事 |
| 设定生成器 | 随机生成角色、场景、情节设定 |
| 创意碰撞 | 多个创意元素组合生成新点子 |

- **使用流程**: 选择模式 → 输入关键词 → 获取创意 → 开始写作

### 📢 公众号发布
- **草稿创建** - 一键生成公众号图文草稿
- **直接发布** - 支持直接发布或保存为草稿
- **评论控制** - 可设置是否开启评论、仅粉丝评论
- **模拟模式** - 支持模拟发布测试，无需真实配置

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

### 方式三：Docker 部署（推荐用于生产）

#### 快速启动（开发环境）

```bash
# 1. 克隆项目
git clone https://github.com/loyd3/joe-ai-writer.git
cd joe-ai-writer

# 2. 配置环境变量
cp .env.docker .env
# 编辑 .env，配置你的 AI API Key

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

访问 http://localhost:5173

#### 生产环境部署

```bash
# 1. 配置生产环境变量
cp .env.docker .env
# 编辑 .env，设置强密码和正式的 API Key

# 2. 构建前端生产版本
cd frontend
npm install
npm run build
cd ..

# 3. 使用生产配置启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 查看服务状态
docker-compose ps
```

访问 http://localhost (Nginx 默认 80 端口)

#### 常用 Docker 命令

```bash
# 查看日志
docker-compose logs -f backend      # 后端日志
docker-compose logs -f frontend     # 前端日志
docker-compose logs -f mysql        # 数据库日志

# 重启服务
docker-compose restart backend

# 进入容器
docker-compose exec backend bash
docker-compose exec mysql mysql -u joewriter -p

# 备份数据库
docker-compose exec mysql mysqldump -u root -p joe_writer > backup.sql

# 完全清理（包括数据卷）
docker-compose down -v
```

#### Docker 服务架构

| 服务 | 端口 | 说明 |
|------|------|------|
| mysql | 3306 | MySQL 8.0 数据库 |
| backend | 8000 | FastAPI 后端服务 |
| frontend | 5173 | Vite 开发服务器 |
| nginx | 80 | 生产环境静态服务器（可选）|

---

## 📁 项目结构

```
joe-ai-writer/
├── start.py                      # 一键启动脚本
├── init_db.py                    # 数据库初始化脚本
├── .env.example                  # 环境变量模板
├── .env.docker                   # Docker 环境变量模板
├── docker-compose.yml            # Docker Compose 配置
├── docker-compose.prod.yml       # Docker 生产环境配置
├── docker-compose.override.yml   # Docker 开发环境覆盖
├── nginx.conf                    # Nginx 配置
├── backend/                      # FastAPI 后端
│   ├── Dockerfile                # 后端 Docker 镜像
│   ├── .dockerignore             # Docker 忽略文件
│   ├── app/
│   │   ├── api/                  # API 路由
│   │   │   ├── ai_story_generator.py   # AI故事生成器
│   │   │   ├── long_article.py         # 长篇文章生成器
│   │   │   ├── auto_write.py           # 自动写作
│   │   │   ├── brainstorm.py           # 脑洞写作
│   │   │   ├── hot_topics.py           # 热点写作
│   │   │   └── ...
│   │   ├── core/                 # AI 客户端和配置
│   │   ├── models/               # 数据库模型
│   │   └── services/             # 业务逻辑
│   ├── database/
│   │   └── init.sql              # 数据库建表 SQL
│   └── requirements.txt
├── frontend/                     # Vue3 前端
│   ├── Dockerfile                # 前端 Docker 镜像
│   ├── .dockerignore             # Docker 忽略文件
│   └── src/
│       ├── components/           # UI 组件
│       ├── stores/               # Pinia 状态管理
│       ├── views/                # 页面视图
│       │   ├── AIStoryGenerator.vue    # AI故事生成器
│       │   ├── LongArticleGenerator.vue # 长篇文章生成器
│       │   ├── AutoWrite.vue           # 自动写作
│       │   ├── BrainstormWriting.vue   # 脑洞写作
│       │   └── ...
│       └── router/               # 路由配置
└── docs/                        # 文档
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
- APScheduler - 定时任务调度（自动写作）
- BeautifulSoup4 - 热点数据抓取

**前端**
- Vue 3 + TypeScript
- Element Plus - UI 组件库
- Pinia - 状态管理
- Axios - HTTP 客户端
- Vue Router - 路由管理
- Markdown-it - Markdown 渲染

---

## 📝 更新日志

### v2.0.0 (2025-03)
- ✅ **AI 故事生成器** - 支持多种故事类型、角色设定、世界观构建
- ✅ **长篇文章生成器** - 支持 10万-100万字超长文章智能生成
- ✅ **自动写作** - 一键生成热点文章，支持自定义主题
- ✅ **脑洞写作** - 创意发散、随机灵感生成、故事接龙
- ✅ **热点增强** - 优化热点抓取和文章生成逻辑
- ✅ **缓存系统** - 新增热点数据缓存服务
- ✅ **文档导出** - 支持长文导出为多种格式

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
