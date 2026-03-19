# 使用国内镜像源（如果官方源慢）
# FROM docker.mirrors.ustc.edu.cn/library/python:3.11-slim
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 (MySQL 客户端等)
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（使用国内镜像源加速，使用CPU版本torch减小体积）
COPY requirements.docker.txt requirements.txt

# 先安装 torch CPU 版本（避免安装完整 CUDA 版本）
# 使用 PyTorch 官方 CPU 仓库
RUN pip install --no-cache-dir --default-timeout=300 \
    torch==2.2.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu

# 再安装其他依赖（使用清华镜像）
RUN pip install --no-cache-dir --default-timeout=300 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制代码
COPY . .

# 确保 init_db.py 可执行
RUN chmod +x init_db.py

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
