# 墨言 快速启动指南

## 1. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置你的 OpenAI API Key

# 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 文档：http://localhost:8000/docs

## 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端地址：http://localhost:5173

## 3. 配置 AI

在项目详情页点击「项目设定」按钮，设置：
- 文章大纲
- 故事线
- 角色设定
- 世界观
- 写作风格

这些信息会在每次 AI 交互时自动注入上下文。

## 4. 功能说明

### 文档编辑器
- 块级编辑（类似 Notion）
- Enter 创建新块
- Backspace 删除空块
- 点击 ⋮ 修改块类型

### AI 助手
- 指导：获取写作建议
- 修改：改写选中的文字
- 润色：优化表达
- 续写：继续下文

### 项目设定系统
每个项目都有独立的记忆空间，AI 会记住：
- 大纲结构
- 角色设定
- 故事线
- 世界观
- 你的写作风格

这让 AI 能在多次对话中保持一致性。
