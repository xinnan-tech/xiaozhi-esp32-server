# Dockerfile for local development and testing
# Build xiaozhi-server image from local source code

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libopus0 \
        ffmpeg \
        build-essential \
        curl \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /opt/xiaozhi-esp32-server

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies with uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Set timezone and Python path
ENV TZ=Asia/Shanghai
ENV PATH="/opt/xiaozhi-esp32-server/.venv/bin:$PATH"

# Expose ports
# 8000: WebSocket server
# 8003: HTTP server for OTA and vision analysis
EXPOSE 8000 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(5); s.connect(('localhost', 8000)); s.close()" || exit 1

# Start application
CMD ["python", "app.py"]

