FROM nvidia/cuda:12.3.2-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# 基础依赖
RUN apt update && apt install -y \
    software-properties-common \
    curl \
    git \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt update -y \
    && apt install -y python3.12 python3.12-venv python3.12-dev \
    && apt clean && rm -rf /var/lib/apt/lists/*

# 安装 pip（自动带上 distutils）
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# 设置默认 python 和 pip
RUN ln -s /usr/bin/python3.12 /usr/bin/python && ln -s /usr/local/bin/pip /usr/bin/pip

WORKDIR /workspace/
EXPOSE 8080


#设置时区timedatectl status｜｜ /etc/timezone 
ENV TimeZone=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TimeZone /etc/localtime && echo $TimeZone > /etc/timezone


COPY requirements.txt /workspace/

COPY . /workspace/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
