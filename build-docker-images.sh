#!/bin/bash
# Docker镜像构建脚本
# 用于在本地或服务器上构建小智服务端的Docker镜像

set -e  # 遇到错误立即退出

echo "=========================================="
echo "小智服务端 Docker 镜像构建脚本"
echo "=========================================="
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到Docker，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "警告: 未检测到Docker Compose，某些功能可能无法使用"
fi

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "项目目录: $SCRIPT_DIR"
echo ""

# 询问是否构建基础镜像
read -p "是否构建 server-base 基础镜像? (y/n, 默认y): " BUILD_BASE
BUILD_BASE=${BUILD_BASE:-y}

# 询问镜像标签
read -p "请输入镜像标签 (默认: latest): " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-latest}

# 构建基础镜像
if [[ "$BUILD_BASE" == "y" || "$BUILD_BASE" == "Y" ]]; then
    echo ""
    echo "=========================================="
    echo "步骤 1/3: 构建 server-base 基础镜像"
    echo "=========================================="
    docker build -t xiaozhi-esp32-server:server-base -f Dockerfile-server-base .
    
    if [ $? -eq 0 ]; then
        echo "✓ server-base 镜像构建成功"
    else
        echo "✗ server-base 镜像构建失败"
        exit 1
    fi
else
    echo "跳过 server-base 镜像构建"
fi

# 构建Server镜像
echo ""
echo "=========================================="
echo "步骤 2/3: 构建 server 镜像"
echo "=========================================="
docker build -t xiaozhi-esp32-server:server_${IMAGE_TAG} -f Dockerfile-server .

if [ $? -eq 0 ]; then
    echo "✓ server 镜像构建成功"
    # 同时打上latest标签
    docker tag xiaozhi-esp32-server:server_${IMAGE_TAG} xiaozhi-esp32-server:server_latest
else
    echo "✗ server 镜像构建失败"
    exit 1
fi

# 构建Web镜像
echo ""
echo "=========================================="
echo "步骤 3/3: 构建 web 镜像 (包含前端和Java后端)"
echo "=========================================="
echo "注意: 此步骤可能需要较长时间（10-30分钟），请耐心等待..."
docker build -t xiaozhi-esp32-server:web_${IMAGE_TAG} -f Dockerfile-web .

if [ $? -eq 0 ]; then
    echo "✓ web 镜像构建成功"
    # 同时打上latest标签
    docker tag xiaozhi-esp32-server:web_${IMAGE_TAG} xiaozhi-esp32-server:web_latest
else
    echo "✗ web 镜像构建失败"
    exit 1
fi

# 显示构建结果
echo ""
echo "=========================================="
echo "构建完成！"
echo "=========================================="
echo ""
echo "已构建的镜像："
docker images | grep xiaozhi-esp32-server | head -5
echo ""
echo "镜像标签："
echo "  - xiaozhi-esp32-server:server_${IMAGE_TAG}"
echo "  - xiaozhi-esp32-server:server_latest"
echo "  - xiaozhi-esp32-server:web_${IMAGE_TAG}"
echo "  - xiaozhi-esp32-server:web_latest"
echo ""
echo "下一步："
echo "1. 将镜像推送到阿里云容器镜像服务（可选）"
echo "2. 在服务器上使用这些镜像部署服务"
echo "3. 参考 docs/aliyun-deployment.md 进行部署"
echo ""

# 询问是否推送到阿里云
read -p "是否推送到阿里云容器镜像服务? (y/n, 默认n): " PUSH_TO_ALIYUN
PUSH_TO_ALIYUN=${PUSH_TO_ALIYUN:-n}

if [[ "$PUSH_TO_ALIYUN" == "y" || "$PUSH_TO_ALIYUN" == "Y" ]]; then
    read -p "请输入阿里云容器镜像服务地址 (例如: registry.cn-hangzhou.aliyuncs.com/your-namespace): " ALIYUN_REGISTRY
    
    if [ -z "$ALIYUN_REGISTRY" ]; then
        echo "错误: 镜像服务地址不能为空"
        exit 1
    fi
    
    echo ""
    echo "正在推送镜像到阿里云..."
    
    # 登录阿里云（如果需要）
    echo "请确保已登录阿里云容器镜像服务:"
    echo "  docker login $ALIYUN_REGISTRY"
    echo ""
    read -p "是否已登录? (y/n): " LOGGED_IN
    if [[ "$LOGGED_IN" != "y" && "$LOGGED_IN" != "Y" ]]; then
        echo "请先登录: docker login $ALIYUN_REGISTRY"
        exit 1
    fi
    
    # 标记镜像
    docker tag xiaozhi-esp32-server:server_latest ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:server_latest
    docker tag xiaozhi-esp32-server:web_latest ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:web_latest
    
    # 推送镜像
    docker push ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:server_latest
    docker push ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:web_latest
    
    echo ""
    echo "✓ 镜像推送完成"
    echo "在服务器上可以使用以下命令拉取镜像："
    echo "  docker pull ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:server_latest"
    echo "  docker pull ${ALIYUN_REGISTRY}/xiaozhi-esp32-server:web_latest"
fi

echo ""
echo "构建脚本执行完成！"


