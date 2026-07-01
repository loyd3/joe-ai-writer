# Windows Docker 部署脚本说明

## 快速开始

### 发布镜像（开发机）

```powershell
cd D:\projects\joe-ai-writer

# 交互式（推荐，双击 deploy-docker.bat 亦可）
.\deploy-docker.bat

# 或 PowerShell 命令行
.\docker-push.ps1 -Version 1.0.0                    # 构建并推送到 Docker Hub
.\docker-push.ps1 -Version 1.0.0 -SkipPush          # 仅构建
.\docker-push.ps1 -ExportOnly                       # 构建并导出 tar
.\docker-push.ps1 -Registry registry.cn-hangzhou.aliyuncs.com/namespace
```

### 部署服务（生产机）

```powershell
# 交互式一键部署
.\install.bat

# 或 PowerShell
.\scripts\windows\deploy.ps1 -Source hub -DockerUser loyd3
.\scripts\windows\deploy.ps1 -Source tar            # 离线 tar 加载
```

### 诊断环境

```powershell
.\diagnose.bat
# 或
.\scripts\windows\diagnose.ps1
```

---

## 脚本结构

| 入口（项目根目录） | 实际脚本 | 用途 |
|-------------------|----------|------|
| `deploy-docker.bat` | `scripts/windows/docker-push.ps1` | 构建镜像、推送或导出 |
| `docker-push.ps1` | 同上（命令行参数） | CI / 自动化发布 |
| `install.bat` | `scripts/windows/deploy.ps1` | 生产环境一键部署 |
| `diagnose.bat` | `scripts/windows/diagnose.ps1` | 环境诊断 |

Mac/Linux 对应脚本：`docker-push.sh`（推送）、`deploy-docker.sh`（本地部署）。

---

## deploy-docker.bat — 构建与发布

功能：

- 构建后端（`backend/Dockerfile`）和前端（`frontend/Dockerfile`）镜像
- 推送到 Docker Hub 或阿里云 ACR
- 导出 tar 到 `docker-images/` 目录（离线部署）
- 自动检测 Docker 是否运行

默认 Docker Hub 用户名为 `loyd3`，可在交互提示中修改，或通过环境变量：

```powershell
$env:DOCKER_USER = "your-username"
.\deploy-docker.bat
```

导出文件位置：

```
docker-images/
├── joe-ai-writer-backend-{version}.tar
└── joe-ai-writer-frontend-{version}.tar
```

---

## install.bat — 生产部署

支持三种镜像来源：

1. **local** — 使用本机已构建的镜像（先运行 `deploy-docker.bat`）
2. **hub** — 从 Docker Hub 拉取（自动更新 `.env.prod` 中的 `DOCKER_REGISTRY`）
3. **tar** — 从 `docker-images/` 加载离线镜像

首次运行会自动从 `.env.prod.example` 创建 `.env.prod`。

**必改配置**（`.env.prod`）：

- `DOCKER_REGISTRY` — Docker Hub 用户名
- `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` — 数据库密码
- `SECRET_KEY` — JWT 密钥
- `CUSTOM_BASE_URL` — Ollama 或 AI API 地址

---

## 部署场景

### 场景 1：本地开发（轻量版 + Ollama）

```powershell
docker compose -f docker-compose-lite.yml up -d
```

### 场景 2：单机生产部署

```powershell
copy .env.prod.example .env.prod
notepad .env.prod
.\install.bat
```

### 场景 3：离线环境

在有网络的机器上：

```powershell
.\deploy-docker.bat   # 选择「导出 tar」
```

将以下文件复制到离线服务器：

- `docker-images/*.tar`
- `docker-compose.prod.yml`
- `.env.prod.example`（或已配置好的 `.env.prod`）
- `install.bat` 及 `scripts/windows/` 目录

在离线服务器上：

```powershell
.\install.bat   # 选择「从 tar 文件加载」
```

### 场景 4：多服务器（Docker Hub）

```powershell
# 发布机
.\deploy-docker.bat   # 推送到 Docker Hub

# 各生产机
.\install.bat         # 从 Docker Hub 拉取
```

---

## 常用运维命令

```powershell
# 启动 / 停止
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml down

# 日志
docker compose -f docker-compose.prod.yml logs -f

# 更新镜像
docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

---

## 常见问题

### Docker 容器无法访问 Ollama

编辑 `.env.prod`：

```env
CUSTOM_BASE_URL=http://host.docker.internal:11434/v1
```

若 Ollama 仅监听 127.0.0.1，以管理员设置：

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "Machine")
```

然后重启 Ollama。

### 修改端口

```env
BACKEND_PORT=9000
FRONTEND_PORT=8080
```

### 数据备份

```powershell
docker exec joe-writer-mysql-prod mysqldump -u root -p joe_writer > backup.sql
```

---

## 目录结构

```
joe-ai-writer/
├── scripts/windows/
│   ├── docker-push.ps1      # 构建与发布（核心逻辑）
│   ├── deploy.ps1           # 生产部署
│   └── diagnose.ps1         # 环境诊断
├── deploy-docker.bat        # 发布入口 ⭐
├── install.bat              # 部署入口 ⭐
├── diagnose.bat             # 诊断入口
├── docker-push.ps1          # 命令行发布（转发）
├── docker-push.sh           # Mac/Linux 发布
├── docker-compose.prod.yml  # 生产 Compose
├── docker-compose-lite.yml  # 轻量开发 Compose
├── docker-images/           # 导出的 tar 镜像（git 忽略）
└── .env.prod.example        # 生产配置模板
```

---

## 支持

1. 运行 `diagnose.bat` 检查环境
2. 查看 `DOCKER_DEPLOY.md` 通用 Docker 文档
3. 查看日志：`docker compose -f docker-compose.prod.yml logs`
