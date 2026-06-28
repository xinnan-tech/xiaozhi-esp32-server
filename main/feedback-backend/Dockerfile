FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 镜像（国内加速）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装 Python 依赖（利用 docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8009

# 生产模式启动（不带 reload，多 worker 提升稳定性与并发）
# 单 worker 时 SQLite/连接池更稳；多 worker 用于高并发。这里用 2 worker 兼顾稳定与性能
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009", "--workers", "1", "--log-level", "info"]
