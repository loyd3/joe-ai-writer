# 使用国内镜像源（如果官方源慢）
# FROM docker.mirrors.ustc.edu.cn/library/node:20-alpine
FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm install

# 复制代码
COPY . .

# 暴露端口
EXPOSE 5173

# 启动命令
CMD ["npm", "run", "dev", "--", "--host"]