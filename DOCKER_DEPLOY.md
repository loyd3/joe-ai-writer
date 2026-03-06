# Joe AI Writer - Docker 本地部署指南

## 快速开始

### 1. 确保 Docker 已安装

```bash
# 检查 Docker
docker --version
docker-compose --version
```

### 2. 一键部署脚本

```bash
cd /Users/loyd/PycharmProjects/joe-ai-writer
./deploy-docker.sh
```

### 3. 或手动部署

#### 方式一：完整部署（推荐）
包含 MySQL 数据库 + 后端 + 前端

```bash
# 复制环境配置
cp .env.docker .env

# 编辑 .env 文件，配置你的 AI API Key
vim .env

# 启动所有服务
docker-compose up -d --build
```

#### 方式二：使用本地 MySQL
如果你本地已有 MySQL

```bash
# 确保 .env 中的数据库连接指向本地 MySQL
# DATABASE_URL=mysql+pymysql://root:password@host.docker.internal:3306/aiwriter

docker-compose -f docker-compose.local-db.yml up -d --build
```

## 访问服务

- **前端界面**: http://localhost:8080
- **后端 API**: http://localhost:9000
- **API 文档**: http://localhost:9000/docs

> 注意：Docker 使用 8080/9000 端口，与本地开发端口（5173/8000）不同，可同时运行互不干扰

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看运行状态
docker-compose ps

# 进入后端容器
docker exec -it joe-writer-backend bash

# 进入数据库容器
docker exec -it joe-writer-mysql mysql -ujoewriter -p
```

## 配置说明

编辑 `.env` 文件配置 AI API：

```env
# 选择 AI 提供商
AI_PROVIDER=deepseek

# DeepSeek API Key (推荐)
DEEPSEEK_API_KEY=your-deepseek-api-key

# 或 OpenAI
# OPENAI_API_KEY=your-openai-api-key

# 或 SiliconFlow
# SILICONFLOW_API_KEY=your-siliconflow-api-key
```

## 故障排查

### 端口被占用
```bash
# 检查 8000 或 5173 端口是否被占用
lsof -i :8000
lsof -i :5173

# 修改 docker-compose.yml 中的端口映射
# ports:
#   - "8080:8000"  # 改为 8080
```

### 数据库连接失败
```bash
# 查看数据库日志
docker-compose logs mysql

# 重新初始化数据库
docker-compose down -v
docker-compose up -d
```

### 前端无法连接后端
检查 `VITE_API_URL` 是否配置正确：
```env
VITE_API_URL=http://localhost:8000
```

## 数据持久化

- MySQL 数据存储在 Docker Volume `mysql_data` 中
- 即使删除容器，数据也不会丢失
- 如需完全重置：`docker-compose down -v`

## 生产环境部署

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d
```
