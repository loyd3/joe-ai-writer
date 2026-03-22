# Joe AI Writer - Windows Docker 一键部署指南

## 🚀 快速开始

### 1. 前置要求

- **Docker Desktop** (Windows 10/11 64位)
  - 下载地址: https://www.docker.com/products/docker-desktop
  - 安装后确保 Docker Desktop 正在运行

### 2. 一键部署

双击运行 `deploy.bat` 文件，或在 PowerShell/CMD 中执行：

```powershell
.\deploy.bat
```

### 3. 首次配置

脚本会自动检测并提示配置：

1. **环境变量** - 首次运行会自动从 `.env.docker` 创建 `.env`
2. **API Key** - 需要配置至少一个 AI 服务的 API Key

编辑 `.env` 文件，配置你的 API Key：

```bash
# DeepSeek (推荐，中文写作优秀)
DEEPSEEK_API_KEY=your-deepseek-api-key

# 或 OpenAI
OPENAI_API_KEY=your-openai-api-key

# 或 SiliconFlow
SILICONFLOW_API_KEY=your-siliconflow-api-key
```

### 4. 访问应用

部署成功后访问：

- **前端界面**: http://localhost:8080
- **后端 API**: http://localhost:9000

## 📋 常用命令

```powershell
# 启动服务（前台运行，查看日志）
.\deploy.bat

# 查看实时日志
.\deploy.bat logs

# 停止服务
.\deploy.bat stop

# 重启服务
.\deploy.bat restart

# 查看服务状态
.\deploy.bat status
```

## 🔧 手动 Docker 命令

如果需要更精细的控制，可以使用以下命令：

```powershell
# 启动所有服务
docker compose up -d

# 构建并启动
docker compose up --build -d

# 查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mysql

# 停止服务
docker compose down

# 停止并删除数据卷（清空数据库）
docker compose down -v

# 重启服务
docker compose restart

# 进入容器
docker compose exec backend bash
docker compose exec mysql mysql -u joewriter -p

# 备份数据库
docker compose exec mysql mysqldump -u root -p joe_writer > backup.sql
```

## 🛠️ 故障排除

### Docker 未安装

```
❌ Docker 未安装或未启动！
```

**解决**: 安装 Docker Desktop 并确保其正在运行。

### 端口被占用

如果 8080 或 9000 端口被占用，修改 `docker-compose.yml`：

```yaml
ports:
  - "8081:5173"  # 改为 8081
```

### 服务启动失败

```powershell
# 查看详细日志
docker compose logs

# 检查容器状态
docker compose ps

# 重新构建
docker compose down
docker compose up --build -d
```

### 数据库连接失败

```powershell
# 检查 MySQL 容器状态
docker compose ps mysql

# 查看 MySQL 日志
docker compose logs mysql

# 手动初始化数据库
docker compose exec backend python init_db.py
```

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `deploy.bat` | Windows 一键部署脚本 |
| `docker-compose.yml` | Docker Compose 配置 |
| `.env` | 环境变量配置（自动生成） |
| `.env.docker` | 环境变量模板 |

## 🔒 安全提示

1. **生产环境**请修改默认密码：
   - `MYSQL_ROOT_PASSWORD`
   - `MYSQL_PASSWORD`
   - `SECRET_KEY`

2. **API Key** 不要提交到代码仓库

3. **对外部署**时建议：
   - 使用 HTTPS
   - 配置防火墙
   - 修改默认端口

## 📝 更新日志

### v1.0.0 (2025-03-20)
- ✅ Windows 一键部署脚本
- ✅ 自动环境检测
- ✅ 自动配置生成
- ✅ 常用命令封装
