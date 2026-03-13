# 🚀 Windows Docker 部署脚本说明

## 快速开始

### 首次部署

```powershell
# 方式1: 一键安装（最简单）
cd D:\projects\joe-ai-writer
.\install.bat

# 方式2: 先构建再部署
.\deploy-docker.bat    # 构建镜像
.\install.bat          # 部署服务
```

### 日常使用

```powershell
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 更新版本
.\update.bat
```

---

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `deploy-docker.bat` | 构建镜像、推送到仓库或导出 |
| `install.bat` | 一键部署到新服务器 |
| `update.bat` | 更新现有部署 |
| `start_local.bat` | 本地开发运行（非 Docker） |
| `diagnose.ps1` | 诊断问题 |

---

## 详细说明

### 1. deploy-docker.bat - 构建发布镜像

功能：
- ✅ 构建后端和前端 Docker 镜像
- ✅ 导出镜像为 tar 文件（便于离线部署）
- ✅ 推送到 Docker Hub
- ✅ 推送到阿里云容器仓库

使用步骤：
1. 修改脚本开头的 `IMAGE_PREFIX` 为你的 Docker Hub 用户名
2. 运行脚本，按提示操作
3. 选择推送目标（Docker Hub / 阿里云 / 本地文件）

输出文件：
- `joe-ai-writer-backend-{version}.tar`
- `joe-ai-writer-frontend-{version}.tar`

---

### 2. install.bat - 一键部署

功能：
- ✅ 检查 Docker 环境
- ✅ 创建配置文件
- ✅ 拉取/加载镜像
- ✅ 启动服务
- ✅ 检查状态

支持三种部署方式：
1. **本地镜像** - 使用刚构建的镜像
2. **Docker Hub** - 从仓库拉取
3. **Tar 文件** - 从导出文件加载（离线部署）

---

### 3. update.bat - 更新服务

功能：
- ✅ 自动备份数据库
- ✅ 拉取新镜像
- ✅ 可选重新构建
- ✅ 重启服务

---

### 4. start_local.bat - 本地开发

功能：
- ✅ 创建 Python 虚拟环境
- ✅ 安装依赖
- ✅ 启动本地后端

适用场景：
- Docker 网络问题无法解决时
- 需要调试后端代码
- Ollama 在 Windows 本地运行

---

## 配置文件

### .env.prod - 生产环境配置

```powershell
# 复制模板
copy .env.prod.example .env.prod

# 编辑配置
notepad .env.prod
```

**必改项**：
- `MYSQL_ROOT_PASSWORD` - 数据库 root 密码
- `MYSQL_PASSWORD` - 数据库用户密码
- `SECRET_KEY` - JWT 密钥
- `CUSTOM_BASE_URL` - Ollama 地址

---

## 部署场景

### 场景1：本地开发测试

```powershell
# 使用轻量版配置
docker-compose -f docker-compose-lite.yml up -d
```

### 场景2：单机生产部署

```powershell
# 1. 配置环境
notepad .env.prod

# 2. 部署
.\install.bat

# 或手动
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

### 场景3：离线环境部署

```powershell
# 在有网络的机器上
cd D:\projects\joe-ai-writer
.\deploy-docker.bat
# 选择导出镜像

# 复制以下文件到离线服务器：
# - joe-ai-writer-backend-latest.tar
# - joe-ai-writer-frontend-latest.tar
# - docker-compose.prod.yml
# - install.bat

# 在离线服务器上
.\install.bat
# 选择 "从 tar 文件加载镜像"
```

### 场景4：多服务器部署

```powershell
# 推送到 Docker Hub
.\deploy-docker.bat
# 选择推送到 Docker Hub

# 在多台服务器上
.\install.bat
# 选择 "从 Docker Hub 拉取镜像"
```

---

## 常见问题

### Q: Docker 容器无法访问 Ollama？

A: 修改 `.env.prod` 中的 `CUSTOM_BASE_URL`：
- Ollama 在宿主机：`http://host.docker.internal:11434/v1`
- Ollama 在其他服务器：`http://192.168.1.100:11434/v1`

### Q: 如何修改端口？

A: 编辑 `.env.prod`：
```env
BACKEND_PORT=9000    # 后端端口
FRONTEND_PORT=8080   # 前端端口
```

### Q: 如何升级版本？

A: 运行 `update.bat` 或手动：
```powershell
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Q: 数据如何持久化？

A: MySQL 数据自动保存在 Docker Volume 中：
```powershell
# 查看数据卷
docker volume ls

# 备份数据
docker exec joe-writer-mysql-prod mysqldump -u root -p joe_writer > backup.sql
```

---

## 端口占用检查

```powershell
# 检查端口占用
netstat -ano | findstr "8080"
netstat -ano | findstr "9000"
netstat -ano | findstr "11434"

# 结束占用进程
taskkill /PID 进程ID /F
```

---

## 目录结构

```
joe-ai-writer/
├── backend/                      # 后端代码
│   ├── Dockerfile               # 生产 Dockerfile
│   └── Dockerfile.lite          # 轻量版 Dockerfile
├── frontend/                     # 前端代码
│   └── Dockerfile
├── deploy-docker.bat            # 构建发布镜像 ⭐
├── install.bat                  # 一键部署 ⭐
├── update.bat                   # 更新服务 ⭐
├── start_local.bat              # 本地运行 ⭐
├── diagnose.ps1                 # 诊断脚本
├── docker-compose.yml           # 开发环境
├── docker-compose-lite.yml      # 轻量开发环境
├── docker-compose.prod.yml      # 生产环境 ⭐
├── .env.prod.example            # 生产配置模板
├── DEPLOY.md                    # 详细部署文档
└── WINDOWS_DEPLOY_README.md     # 本文档
```

---

## 支持

遇到问题？
1. 运行 `diagnose.ps1` 检查环境
2. 查看 `DEPLOY.md` 详细文档
3. 检查 Docker 日志：`docker-compose -f docker-compose.prod.yml logs`
