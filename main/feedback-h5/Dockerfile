FROM python:3.10-slim

WORKDIR /app

# 配置 pip 镜像（国内加速）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装 aiohttp（start.py 唯一依赖）
RUN pip install --no-cache-dir aiohttp==3.11.10

# 复制 H5 全部文件（静态资源 + start.py）
COPY . .

# 暴露端口
EXPOSE 8007

# 启动 H5 服务器 + 反向代理
CMD ["python", "start.py"]
