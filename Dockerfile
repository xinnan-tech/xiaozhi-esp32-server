# 第一阶段：前端构建
FROM node:18 AS frontend-builder

WORKDIR /app/ZhiKongTaiWeb

# 使用 Yarn 作为包管理工具
COPY ZhiKongTaiWeb/package.json ZhiKongTaiWeb/yarn.lock ./

RUN corepack enable && yarn install --frozen-lockfile

COPY ZhiKongTaiWeb .

RUN yarn build

# 第二阶段：构建 Python 依赖
FROM python:3.10-slim AS builder

WORKDIR /app

COPY pyproject.toml .

# 使用 Poetry 安装 Python 依赖
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# 第三阶段：生产镜像
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-esp32-server

# 使用清华源加速apt安装
RUN rm -rf /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libopus0 ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Poetry 依赖和前端构建产物
COPY --from=builder /app /opt/xiaozhi-esp32-server
COPY --from=frontend-builder /app/ZhiKongTaiWeb/dist /opt/xiaozhi-esp32-server/manager/static

# 复制应用代码
COPY . .

# 启动应用
CMD ["python", "app.py"]
