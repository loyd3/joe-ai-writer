# 📝 墨心 - AI 智能写作助手

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
- **AI 插图** - 根据正文生成配图并插入

### 🔥 热点写作
| 功能 | 说明 |
|------|------|
| 热点抓取 | 自动抓取微博、知乎、百度、头条等平台热搜 |
| AI 大纲生成 | 根据热点自动生成文章结构和标题选项 |
| AI 文章写作 | 流式生成完整文章内容 |
| 一键保存 | 直接保存到项目，无缝衔接编辑 |

### 🤖 AI 故事生成器
支持玄幻、科幻、言情、悬疑、武侠、都市等多种故事类型，包含角色设定、世界观构建、情节大纲生成和智能续写。

### 📚 长篇文章生成器
支持生成 10万-100万字超长文章，智能分章节、断点续写、多种风格可选。

### 💡 脑洞写作
创意发散、随机灵感、故事接龙、设定生成器、创意碰撞。

### 📢 公众号发布
一键生成公众号图文草稿，支持直接发布或保存为草稿。

---

## 🚀 快速开始

### 前置要求
- **MySQL 数据库**（默认使用本地 MySQL）
- **Node.js** (v20+) 和 **Python** (v3.11+)

### 方式一：一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-writer.git
cd joe-ai-writer

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置你的 AI API Key 和数据库连接

# 初始化数据库
python init_db.py

# 一键启动
python start.py
```

访问 http://localhost:5173

### 方式二：Docker 部署

```bash
cp .env.docker .env
# 编辑 .env，配置你的 AI API Key

# Windows
.\deploy.bat

# macOS / Linux
chmod +x deploy.sh && ./deploy.sh
```

访问 http://localhost:8080（后端 API：http://localhost:9000）。详见 [DOCKER_DEPLOY.md](./DOCKER_DEPLOY.md)。

---

## 🛠️ 技术栈

**后端**
- FastAPI + SQLAlchemy + OpenAI SDK

**前端**
- Vue 3 + TypeScript + Element Plus + Pinia

---

## 📄 许可证

[MIT License](./LICENSE)

---

<p align="center">Made with ❤️ by <a href="https://github.com/loyd3">loyd3</a></p>
