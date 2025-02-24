# 第一阶段：前端构建

FROM kalicyh/node:v18-alpine AS frontend-builder

WORKDIR /app/ZhiKongTaiWeb

# RUN corepack enable && yarn config set registry https://registry.npmmirror.com

COPY ZhiKongTaiWeb/package.json ZhiKongTaiWeb/yarn.lock ./

RUN yarn install --frozen-lockfile

COPY ZhiKongTaiWeb . 
RUN yarn build

# 第二阶段：构建 Python 依赖

FROM kalicyh/poetry:v3.10_xiaozhi AS builder

WORKDIR /app

# 同时拷贝本地环境.venv
COPY . .
# 检查是否有缺失
RUN poetry install --no-root

# 使用清华源加速apt安装，该镜像内置所以注释
# RUN rm -rf /etc/apt/sources.list.d/* && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
#     apt-get update && \
#     apt-get install -y --no-install-recommends libopus0 ffmpeg && \
#     apt-get clean

# 从构建阶段复制虚拟环境和前端构建产物
COPY --from=frontend-builder /app/ZhiKongTaiWeb/dist /app/manager/static/webui

# 设置虚拟环境路径
ENV PATH="/app/.venv/bin:$PATH"

# 启动应用
ENTRYPOINT ["poetry", "run", "python"]
CMD ["app.py"]