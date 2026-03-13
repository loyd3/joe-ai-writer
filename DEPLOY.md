# 墨心 AI 写作工具 - Docker 部署指南

## 快速开始

### 1. 本地构建并运行

```powershell
# 进入项目目录
cd D:\projects\joe-ai-writer

# 运行部署脚本（构建镜像）
.\deploy-docker.bat

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 使用预构建镜像

```powershell
# 复制环境配置
copy .env.prod.example .env.prod

# 编辑 .env.prod，修改镜像地址和配置
notepad .env.prod

# 启动
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 部署方式

### 方式一：单机部署（最简单）

在一台服务器上运行所有服务：

```powershell
cd D:\projects\joe-ai-writer

# 1. 配置环境变量
notepad .env.prod

# 2. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 方式二：导出镜像到离线环境

```powershell
# 1. 构建并导出镜像
.\deploy-docker.bat

# 2. 将以下文件复制到目标服务器：
#    - joe-ai-writer-backend-latest.tar
#    - joe-ai-writer-frontend-latest.tar
#    - docker-compose.prod.yml
#    - .env.prod

# 3. 在目标服务器加载镜像
docker load -i joe-ai-writer-backend-latest.tar
docker load -i joe-ai-writer-frontend-latest.tar

# 4. 启动
docker-compose -f docker-compose.prod.yml up -d
```

### 方式三：推送到 Docker Hub

```powershell
# 1. 登录 Docker Hub
docker login

# 2. 修改 deploy-docker.bat 中的 IMAGE_PREFIX
set IMAGE_PREFIX=your-dockerhub-username

# 3. 运行部署脚本，选择推送到 Docker Hub
.\deploy-docker.bat

# 4. 在任何服务器上拉取并运行
docker pull your-dockerhub-username/joe-ai-writer-backend:latest
docker pull your-dockerhub-username/joe-ai-writer-frontend:latest
docker-compose -f docker-compose.prod.yml up -d
```

## 配置说明

### 必改配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | 随机生成强密码 |
| `MYSQL_PASSWORD` | MySQL 应用密码 | 随机生成强密码 |
| `SECRET_KEY` | JWT 密钥 | 随机生成长字符串 |
| `CUSTOM_BASE_URL` | Ollama 地址 | 根据实际环境修改 |

### Ollama 地址配置

| 场景 | 配置值 |
|------|--------|
| Ollama 在宿主机 | `http://host.docker.internal:11434/v1` |
| Ollama 在同一服务器 | `http://localhost:11434/v1` |
| Ollama 在其他服务器 | `http://192.168.1.100:11434/v1` |
| 使用 OpenAI | `https://api.openai.com/v1` |

## 常用命令

```powershell
# 启动
docker-compose -f docker-compose.prod.yml up -d

# 停止
docker-compose -f docker-compose.prod.yml down

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml logs -f backend

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 更新镜像后重启
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 进入容器调试
docker exec -it joe-writer-backend-prod bash

# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 备份数据库
docker exec joe-writer-mysql-prod mysqldump -u root -p joe_writer > backup.sql

# 恢复数据库
docker exec -i joe-writer-mysql-prod mysql -u root -p joe_writer < backup.sql
```

## 目录结构

```
joe-ai-writer/
├── backend/              # 后端代码
├── frontend/             # 前端代码
├── deploy-docker.bat     # 构建发布脚本
├── docker-compose.yml    # 开发环境配置
├── docker-compose-lite.yml  # 轻量开发配置
├── docker-compose.prod.yml  # 生产环境配置
├── .env.prod.example     # 生产环境配置模板
└── DEPLOY.md             # 本文件
```

## 故障排查

### 容器无法启动

```powershell
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs

# 检查端口占用
netstat -ano | findstr "9000"
netstat -ano | findstr "8080"
```

### 数据库连接失败

```powershell
# 检查 MySQL 状态
docker exec joe-writer-mysql-prod mysqladmin -u root -p ping

# 重置数据库（谨慎操作！）
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### AI 功能无法使用

1. 检查 Ollama 是否可访问
2. 确认 `CUSTOM_BASE_URL` 配置正确
3. 检查容器是否能访问宿主机网络

## 安全建议

1. **修改所有默认密码**
2. **使用 HTTPS**（配置 Nginx 反向代理）
3. **限制端口暴露**（仅暴露 80/443）
4. **定期备份数据库**
5. **更新镜像版本**
