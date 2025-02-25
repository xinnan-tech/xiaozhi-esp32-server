# 第一阶段：构建依赖
FROM python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .

# 安装构建依赖
RUN sudo apt-get update && \
    sudo apt-get install -y --no-install-recommends \
    gcc \
    libopus-dev \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 安装Python依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 第二阶段：生产镜像
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-es32-server

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libopus0 \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置虚拟环境路径
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 启动应用
CMD ["python", "app.py"]