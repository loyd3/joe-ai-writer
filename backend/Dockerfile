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

# 安装 Python 依赖（使用国内镜像源加速，使用 CPU 版 torch 减小体积）
COPY requirements.docker.txt requirements.txt

# torch：仅用官方 CPU 索引（2.2.0+cpu 等 +cpu 版本已从索引移除，会装失败）
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --default-timeout=600 \
    torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu

# 其余依赖：清华镜像 + PyTorch CPU 作额外索引，避免 sentence-transformers 等把 torch 换成 CUDA 大包
RUN pip install --no-cache-dir --default-timeout=600 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# 复制代码
COPY . .

# 确保 init_db.py 可执行
RUN chmod +x init_db.py

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
