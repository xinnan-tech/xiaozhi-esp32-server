#!/bin/bash
# Raspberry Pi ARM64 Setup Script for XiaoZhi Server (ESP32 Backend)

set -e  # Exit immediately if any command fails

# ==== ARM64 Banner & Author ====
echo -e "\e[1;32m"  # Bright green color
cat << "EOF"
Reference: VanillaNahida
Author: Huynh Tran
     _    ____   __  __ 
    / \  |  _ \ |  \/  |
   / _ \ | |_) || |\/| |
  / ___ \|  _ < | |  | |
 /_/   \_\_| \_\|_|  |_|
EOF
echo -e "\e[0m"  # Reset color
echo -e "\e[1;36m  ARM64 Architecture Deployment Script - Author: Huynh Tran \e[0m\n"
sleep 1
# ==== End of Banner ====

# ========== 1. Create required directories ==========
BASE_DIR="/main/xiaozhi-server"
DATA_DIR="$BASE_DIR/data"
MODEL_DIR="$BASE_DIR/models/SenseVoiceSmall"

echo "📁 Checking and creating directory structure..."
[ -d "$DATA_DIR" ] && echo "✅ Data directory exists. Skipping..." || mkdir -p "$DATA_DIR"
[ -d "$MODEL_DIR" ] && echo "✅ Model directory exists. Skipping..." || mkdir -p "$MODEL_DIR"

# ========== 2. Download AI voice model ==========
MODEL_URL="https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt"
MODEL_PATH="$MODEL_DIR/model.pt"

if [ ! -f "$MODEL_PATH" ]; then
    echo "📥 Downloading voice recognition model..."
    curl -fL --progress-bar "$MODEL_URL" -o "$MODEL_PATH"
else
    echo "✅ Model already downloaded at $MODEL_PATH. Skipping..."
fi

# ========== 3. Install Docker & buildx support ==========
if ! command -v docker >/dev/null 2>&1; then
    echo "🐳 Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
else
    echo "✅ Docker already installed. Skipping..."
fi

# Enable buildx (if not already enabled)
if ! docker buildx ls >/dev/null 2>&1; then
    echo "🔧 Enabling Docker buildx..."
    docker buildx create --use
else
    echo "✅ Buildx already enabled. Skipping..."
fi

# ========== 4. Build Docker Image for ARM64 ==========
IMAGE_NAME="xiaozhi-esp32-server:server-base"
if ! docker image inspect $IMAGE_NAME >/dev/null 2>&1; then
    echo "🏗️ Building backend Docker image for ARM64..."
    docker buildx build --no-cache --platform linux/arm64 \
        -t $IMAGE_NAME \
        -f ./Dockerfile-server-base \
        .
else
    echo "✅ Image $IMAGE_NAME already exists. Skipping build..."
fi

# ========== 5. Run Docker Compose (ARM64) ==========
COMPOSE_FILE="$(pwd)/main/xiaozhi-server/docker-compose_arm.yml"

if [ -f "$COMPOSE_FILE" ]; then
    echo "🚀 Starting services with Docker Compose (ARM64)..."
    docker compose -f "$COMPOSE_FILE" up -d --build
else
    echo "❌ Docker Compose file not found at $COMPOSE_FILE"
    exit 1
fi

# ========== 6. Prompt user for server.secret ==========
PUBLIC_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "🔗 Server management panel addresses:"
echo "  - Local: http://127.0.0.1:8002/"
echo "  - Public: http://$PUBLIC_IP:8002/"
echo ""
echo "Open the above link in your browser and register the first admin account."
echo "Then log in → Go to 'More' → 'Parameter Management' → Find entry with Code: server.secret"
echo "Copy its value and paste it below."
echo ""

read -p "Please enter server.secret (leave blank to skip): " SECRET_KEY

# ========== 7. Write secret-key into config ==========
CONFIG_FILE="$DATA_DIR/.config.yaml"
if [ -n "$SECRET_KEY" ]; then
    echo "🔑 Checking if pyyaml is installed..."
    if ! python3 -c "import yaml" >/dev/null 2>&1; then
        echo "⚠️ Module pyyaml not found. Installing with apt..."
        sudo apt-get install -y python3-yaml
    else
        echo "✅ pyyaml is already installed."
    fi
    echo "🔑 Writing secret key into $CONFIG_FILE ..."
    python3 - <<EOF
import yaml, os
config_path = "$CONFIG_FILE"
config = {}
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
config['manager-api'] = {
    'url': 'http://xiaozhi-esp32-server-web:8002/xiaozhi',
    'secret': '$SECRET_KEY'
}
with open(config_path, "w") as f:
    yaml.dump(config, f, allow_unicode=True)
EOF
    docker restart xiaozhi-esp32-server
    echo "✅ Secret key added and container restarted."
else
    echo "⚠️ No secret key provided. Skipping configuration update..."
fi

# ========== 8. Display summary ==========
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Installation completed successfully!"
echo "---------------------------------------------"
echo "Admin Panel:       http://$LOCAL_IP:8002"
echo "OTA Endpoint:      http://$LOCAL_IP:8002/xiaozhi/ota/"
echo "Vision API:        http://$LOCAL_IP:8003/mcp/vision/explain"
echo "WebSocket:         ws://$LOCAL_IP:8000/xiaozhi/v1/"
echo "---------------------------------------------"
echo "🎉 Setup finished! You can now access the web dashboard."
