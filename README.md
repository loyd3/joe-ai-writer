# 📝 墨心 - AI 智能写作助手

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/vue-3-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 登录后的写作工作台。项目里保存大纲、人物、故事线和正文；右下角的「小墨」按这些设定改稿、补设定，或逐章成文。

---

## 现在的产品

登录后左侧是：我的项目、数据看板、热点写作、脑洞写作、文案写作、AI 故事生成。顶部可全局搜索。账号菜单里有文风库、大模型设置和主题。

每个项目是一棵文档树，加上右侧抽屉里的项目设定（大纲、角色、故事线、世界观、文风、要点、备注）。文档用块编辑器书写，可按章节拆分、导出，也可发布到公众号或转成视频文案。

模型分两条通道，侧边栏可随时切换：

- **线上**：DeepSeek（默认）、OpenAI、SiliconFlow、意心 YXAI，或任意 OpenAI 兼容接口
- **本地**：Ollama（默认模型 `qwen2.5:14b`，地址 `http://localhost:11434/v1`）

---

## 小墨

页面右下角打开「小墨助手」。它跟着当前页面走：

- **文档页**：改正在编辑的这一篇；有选区时直接改选中的段落
- **项目页**：管整本的文档和设定
- **还没进项目**：可以先聊、先做专项写作，需要落盘时创建项目并绑定这次对话

同一项目里的多轮对话会接着上文，但以刚发出的这条指令为准。更早的内容只作参考，不会自动续做上一轮没说完的步骤。上下文过长时会丢掉历史，只执行当前指令。

| 你怎么说 | 小墨怎么做 |
|----------|------------|
| 润色、改写、扩写当前段落 | 按编辑焦点改对应块。长文先看目录和摘要，再按页阅读、按块修改 |
| 改人物、故事线、大纲、世界观、文风、要点、备注 | 增量合并进本项目设定 |
| 根据设定生成多篇 / 多章 | 按本项目的角色、故事线、世界观、文风和大纲逐章写作并写入文档，正文不灌进对话 |
| 检查设定是否矛盾 | 对照人物、时间线和情节，指出问题并可提案修改 |
| 热点、脑洞、营销文案、故事设定 | 走对应写作流程，再把成稿或设定写入项目 |
| 删除某篇文档 | 先给出删除提案，必须在对话里确认才会删除 |
| 还没有项目 | 讨论可直接结束；要保存正文或设定时先创建项目 |

改稿和设定会写入项目，对话里可以撤销。删除不会自动执行。

热点、脑洞、文案、故事页面仍然可以单独打开。小墨的区别是对着这一本项目的设定和正文来写，不另起一套人设。

---

## 项目里的其他能力

- **项目设定**：每个项目一份记忆。生成章节、自动写作和小墨都会带上这些内容。
- **AI 自动写作**：在项目里按大纲勾选章节，逐章生成并写入对应文档。需要先有大纲。
- **文学作品分析**：导入文本，拆成角色、故事线和大纲等设定。
- **模板**：首页可从预设模板建项目，也可把模板导入已有项目。
- **导入导出**：项目可导出为 Markdown 或 JSON 项目包，项目包能再导入成新项目。单篇文档可导出 Markdown / 文本。
- **文风库**：账号级文风，可选用预设，或从 txt、md、docx、pdf 范文提炼后跨项目复用。
- **块编辑器**：块级正文、自动保存；服务器版本冲突时会暂停自动保存，避免盖掉远端稿。
- **专项写作**：热点抓取与成文、脑洞、营销文案、多类型故事生成。成稿可保存到项目，也可转视频文案或走公众号草稿。
- **数据看板**：项目数、文档数、字数和 AI 使用情况。
- **公众号**：配置 `WECHAT_APP_ID` / `WECHAT_APP_SECRET` 后，可把成稿存成图文草稿或发布。

后端仍保留长文计划接口（`/api/long-article`）。当前主界面没有单独的长文入口，多章写作走项目里的「AI 自动写作」或小墨的「根据设定生成多篇」。

---

## 快速开始

需要本机 **MySQL**、**Python 3.11+**、**Node.js 20+**。

```bash
git clone https://github.com/loyd3/joe-ai-writer.git
cd joe-ai-writer

cp .env.example .env
# 填写 DATABASE_URL 和 DEEPSEEK_API_KEY（或其他模型的 Key）

python init_db.py
python start.py
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

`start.py` 会检查本机 MySQL，再同时拉起后端和前端。端口可用 `--backend-port`、`--frontend-port` 修改。

Docker 部署见 [DOCKER_DEPLOY.md](./DOCKER_DEPLOY.md)（默认前端 http://localhost:8080，后端 http://localhost:9000）。

---

## 技术栈

**后端** FastAPI、SQLAlchemy、MySQL、OpenAI 兼容 SDK

**前端** Vue 3、TypeScript、Element Plus、Pinia、Vite

---

## 许可证

[MIT License](./LICENSE)

---

<p align="center">Made with ❤️ by <a href="https://github.com/loyd3">loyd3</a></p>
