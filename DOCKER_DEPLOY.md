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

| 项 | 默认值 |
|----|--------|
| 主机 | `mysql`（compose 服务名） |
| 端口 | `3306`（仅容器网络内） |
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
.\deploy.bat status       # 查看状态
.\deploy.bat restart      # 重启
.\deploy.bat down         # 停止

# 等价 docker compose 命令
docker compose up -d --build
docker compose logs -f
docker compose ps
docker compose down
docker compose down -v    # 停止并删除 MySQL 数据卷（慎用）
```

## 说明

- Docker 前端 **8080**、后端 **9000**，与本地开发（5173 / 8000）互不冲突
- MySQL **未映射到宿主机**，仅后端容器可访问；需要本机工具连接时再在 `docker-compose.yml` 的 `mysql` 下加 `ports: ["3307:3306"]`
- 数据持久化在 Docker Volume `mysql_data`
