# 第一阶段：前端构建
FROM node:18 AS frontend-builder

WORKDIR /app/ZhiKongTaiWeb

RUN corepack enable && yarn config set registry https://registry.npmmirror.com

COPY ZhiKongTaiWeb/package.json ZhiKongTaiWeb/yarn.lock ./

RUN mkdir node_modules && yarn install --frozen-lockfile

COPY ZhiKongTaiWeb . 
RUN yarn build

# 第二阶段：构建 Python 依赖
FROM ccr.ccs.tencentyun.com/kalicyh/poetry:v3.10_latest AS builder
WORKDIR /app
COPY pyproject.toml poetry.lock  /app/
RUN poetry install --no-root

# 第三阶段：生产镜像
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-esp32-server

# 使用清华源加速apt安装
RUN rm -rf /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends libopus0 ffmpeg && \
    apt-get clean

# 从构建阶段复制虚拟环境和前端构建产物
COPY --from=builder /app/.venv /opt/venv
COPY --from=frontend-builder /app/ZhiKongTaiWeb/dist /opt/xiaozhi-esp32-server/manager/static/webui
# 设置虚拟环境路径
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 启动应用
CMD ["python", "app.py"]