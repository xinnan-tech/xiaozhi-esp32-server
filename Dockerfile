<<<<<<< HEAD
# 第一阶段：构建Python依赖
FROM python:3.10-slim AS builder
=======
# 第一阶段：构建 Python 依赖
FROM kalicyh/poetry:v3.10_xiaozhi AS builder
>>>>>>> f7e7726bea47a5fc28971f49723df956bd58c397

WORKDIR /app

COPY main/xiaozhi-server/requirements.txt .

<<<<<<< HEAD
# 优化apt安装
RUN pip install --no-cache-dir -r requirements.txt

# 第三阶段：生产镜像
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-esp32-server

# 优化apt安装
RUN apt-get update && \
    apt-get install -y --no-install-recommends libopus0 ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python包和前端构建产物
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 复制应用代码
COPY main/xiaozhi-server/ .
=======
# 设置虚拟环境路径
ENV PATH="/app/.venv/bin:$PATH"
>>>>>>> f7e7726bea47a5fc28971f49723df956bd58c397

# 启动应用
CMD ["python", "app.py"]