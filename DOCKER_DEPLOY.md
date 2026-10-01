# Joe AI Writer - Docker 部署

## 保留的文件

| 文件 | 作用 |
|------|------|
| `deploy.bat` | Windows 一键入口（启动 / 停止 / 日志） |
| `docker-compose.yml` | MySQL + 后端 + 前端 |
| `docker-compose.override.yml` | 本地开发覆盖（自动加载） |
| `backend/Dockerfile` | 后端镜像 |
| `frontend/Dockerfile` | 前端镜像 |
| `.env.docker` | Docker 环境变量模板 |

## 磁盘策略（不占 C 盘）

| 内容 | 位置 |
|------|------|
| MySQL 数据 | `F:\joe-ai-writer\docker-data\mysql` |
| 搜索索引 | `F:\joe-ai-writer\docker-data\search_index` |
| HF / 向量模型缓存 | `F:\joe-ai-writer\docker-data\hf-cache` |
| 后端其它数据 | `F:\joe-ai-writer\docker-data\backend-data` |
| Docker 镜像 / 构建缓存 | Docker Desktop 磁盘（建议 junction 到 `F:\Docker\wsl\disk`） |

可通过 `.env` 中 `DOCKER_DATA_ROOT` 修改数据根目录。

当前机器若已将 `%LOCALAPPDATA%\Docker\wsl\disk` junction 到 `F:\Docker\wsl\disk`，则镜像层也不占 C 盘。

## 快速开始

1. 安装并启动 [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. 配置环境变量：

```powershell
copy .env.docker .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY（或其他 AI Key）
```

3. 启动：

```powershell
.\deploy.bat
# 或
docker compose up -d --build
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080 |
| 后端 API | http://localhost:9000 |
| API 文档 | http://localhost:9000/docs |

## 容器内数据库

后端通过 Docker 网络连接 MySQL，**不要用 localhost**：

```
mysql+pymysql://joewriter:joewriter123@mysql:3306/joe_writer?charset=utf8mb4
```

宿主机工具连接（已映射）：

```
mysql://joewriter:joewriter123@localhost:3307/joe_writer
```

| 项 | 默认值 |
|----|--------|
| 主机（容器内） | `mysql`（compose 服务名） |
| 端口（容器内） | `3306` |
| 宿主机端口 | `3307` |
| 库名 | `joe_writer` |
| 用户 | `joewriter` / `joewriter123` |
| root | `root` / `rootpassword` |

进入数据库容器：

```powershell
docker exec -it joe-writer-mysql mysql -ujoewriter -pjoewriter123 joe_writer
```

## 常用命令

```powershell
.\deploy.bat              # 构建并启动
.\deploy.bat logs         # 查看日志
.\deploy.bat status       # 查看状态与磁盘
.\deploy.bat restart      # 重启
.\deploy.bat down         # 停止（保留 F 盘数据）
.\deploy.bat prune        # 清理无用镜像/构建缓存

docker compose up -d --build
docker compose logs -f
docker compose ps
docker compose down
```

## 从本地 MySQL 迁移数据

本地库 `aiwriter@3306` → Docker 库 `joe_writer@3307`（数据在 `F:\joe-ai-writer\docker-data\mysql`）：

```powershell
.\migrate-local-db-to-docker.bat
```

迁移后可用原账号登录 Docker 前端 http://localhost:8080 。
