# ============================================
# Joe AI Writer - 端口配置说明
# ============================================

## 端口分配方案

为避免本地开发和 Docker 部署互相干扰，采用以下端口分配：

| 环境 | 前端端口 | 后端端口 | 访问地址 |
|------|----------|----------|----------|
| **本地开发** | 5173 | 8000 | http://localhost:5173 |
| **Docker 部署** | 8080 | 9000 | http://localhost:8080 |

## 使用方式

### 1. 本地开发（推荐开发时使用）

启动本地服务：

```bash
# 1. 启动后端（端口 8000）
cd backend
python start.py

# 2. 启动前端（端口 5173）
cd frontend
npm run dev

# 访问: http://localhost:5173
```

### 2. Docker 部署（推荐测试/生产使用）

```bash
# 启动 Docker 服务（前端 8080，后端 9000）
docker-compose up -d

# 访问: http://localhost:8080
# API 文档: http://localhost:9000/docs
```

## 同时运行两种环境

由于端口不同，你可以同时运行本地开发和 Docker：

```bash
# 终端 1: 本地开发
python start.py          # 后端 http://localhost:8000
npm run dev              # 前端 http://localhost:5173

# 终端 2: Docker
docker-compose up -d     # 前端 http://localhost:8080
                         # 后端 http://localhost:9000
```

## 常见问题

### 端口被占用

如果提示端口冲突：

```bash
# 检查端口占用
lsof -i :8000    # 本地后端
lsof -i :5173    # 本地前端
lsof -i :9000    # Docker 后端
lsof -i :8080    # Docker 前端

# 释放端口（停止对应服务）
docker-compose down          # 停止 Docker
Ctrl+C                       # 停止本地服务
```

### 切换环境

开发时：http://localhost:5173
测试 Docker：http://localhost:8080

两个环境数据独立（数据库配置不同）
