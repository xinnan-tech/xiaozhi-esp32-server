# 第一阶段：构建 Python 依赖
FROM kalicyh/poetry:v3.10_xiaozhi AS builder

WORKDIR /opt/xiaozhi-esp32-server

# 同时拷贝本地环境.venv
COPY . .
# 检查是否有缺失
RUN poetry install --no-root

# 设置虚拟环境路径
ENV PATH="/app/.venv/bin:$PATH"

# 启动应用
ENTRYPOINT ["poetry", "run", "python"]
CMD ["app.py"]