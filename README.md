# 📝 Joe AI Writer

[![CI/CD](https://github.com/loyd3/joe-ai-writer/actions/workflows/ci.yml/badge.svg)](https://github.com/loyd3/joe-ai-writer/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 一款支持 AI 记忆的智能写作助手，类似 Notion 的块级编辑器 + 具备长期记忆的 AI 协作。

[在线演示](https://your-demo-link.com) · [快速开始](#快速开始) · [功能介绍](#功能特性) · [API 文档](./docs/API.md)

---

## ✨ 功能特性

### 🧠 AI 记忆系统
- **项目级记忆** - 每个项目独立记忆空间
- **智能上下文注入** - 自动在 AI 对话中引用记忆
- **结构化存储** - 大纲、角色、故事线、世界观分类管理

### ✍️ 编辑器
- **块级编辑** - 类似 Notion 的流畅体验
- **快捷键支持** - `/` 快速命令、`Ctrl+Enter` 发送
- **实时保存** - 自动保存到数据库

### 🤖 AI 助手
| 功能 | 说明 |
|------|------|
| 指导 | 获取写作建议和方向 |
| 修改 | 根据要求改写选中文字 |
| 润色 | 优化表达，提升质量 |
| 续写 | 根据上下文继续创作 |
| 对话 | 自由问答，保留记忆 |

---

## 🚀 快速开始

### 本地开发

```bash
# 克隆项目
git clone https://github.com/loyd3/joe-ai-writer.git
cd joe-ai-writer

# 启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置 OpenAI API Key
uvicorn app.main:app --reload

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### Docker 部署

```bash
# 配置环境变量
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=gpt-4

# 启动全部服务
docker-compose up -d
```

---

## 📁 项目结构

```
joe-ai-writer/
├── backend/              # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/         # REST API
│   │   ├── core/        # AI 客户端、配置
│   │   ├── models/      # 数据库模型
│   │   └── services/    # 业务逻辑
│   └── tests/
├── frontend/            # Vue3 + Element Plus
│   └── src/
│       ├── components/  # 编辑器、AI 面板
│       ├── views/       # 页面
│       └── stores/      # Pinia 状态管理
└── .github/workflows/   # CI/CD
```

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///./joe_writer.db` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 必填 |
| `OPENAI_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 使用模型 | `gpt-4` |
| `SECRET_KEY` | JWT 密钥 | 随机生成 |

---

## 🛠️ 技术栈

**后端**
- FastAPI - 高性能 Python Web 框架
- SQLAlchemy - ORM 数据库操作
- OpenAI - AI 能力接入
- Pydantic - 数据验证

**前端**
- Vue 3 - 渐进式 JS 框架
- Element Plus - UI 组件库
- Pinia - 状态管理
- TipTap (计划) - 富文本编辑器

**部署**
- Docker & Docker Compose
- GitHub Actions CI/CD

---

## 📸 截图

> 项目列表页
> ![Projects](./docs/screenshots/projects.png)

> 文档编辑器
> ![Editor](./docs/screenshots/editor.png)

> AI 记忆管理
> ![Memory](./docs/screenshots/memory.png)

---

## 🗺️ 路线图

- [x] 基础编辑器
- [x] AI 记忆系统
- [x] 流式 AI 响应
- [ ] 用户认证系统
- [ ] 文档版本历史
- [ ] Markdown/PDF 导出
- [ ] 协作编辑
- [ ] 移动端适配

详见 [TODO.md](./TODO.md)

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