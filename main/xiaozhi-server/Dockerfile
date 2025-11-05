# Dockerfile for local development and testing
# Build xiaozhi-server image from local source code

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libopus0 \
        ffmpeg \
        build-essential \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure pip to use Aliyun mirror for faster downloads in China
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 120 && \
    pip config set install.retries 5

# Set working directory
WORKDIR /opt/xiaozhi-esp32-server

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt --default-timeout=120 --retries 5

# Copy application code
COPY . .

# Set timezone
ENV TZ=Asia/Shanghai

# Expose ports
# 8000: WebSocket server
# 8003: HTTP server for OTA and vision analysis
EXPOSE 8000 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(5); s.connect(('localhost', 8000)); s.close()" || exit 1

# Start application
CMD ["python", "app.py"]

