FROM nvidia/cuda:12.3.2-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt update && apt install -y \
    software-properties-common \
    curl \
    git \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt update -y \
    && apt install -y python3.12 python3.12-venv python3.12-dev \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspace/
EXPOSE 18000

# Set timezone
ENV TimeZone=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TimeZone /etc/localtime && echo $TimeZone > /etc/timezone

# Copy project files
COPY pyproject.toml uv.lock* /workspace/

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY . /workspace/

CMD ["uv", "run", "python", "main.py"]
