# 第一阶段：构建依赖
FROM python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .

# 安装构建依赖
ARG DEPENDENCIES="  \
    ca-certificates \
    libsox-dev \
    build-essential \
    cmake \
    libasound-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && echo "no" | dpkg-reconfigure dash


# 安装Python依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 第二阶段：生产镜像
FROM python:3.10-slim

WORKDIR /opt/xiaozhi-es32-server

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 安装运行时依赖
ARG DEPENDENCIES="  \
    libopus0 \
    ffmpeg"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && echo "no" | dpkg-reconfigure dash

# 设置虚拟环境路径
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 启动应用
CMD ["./entrypoint-api.sh"]