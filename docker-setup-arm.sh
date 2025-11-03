#!/bin/sh
# Author: Huynh (Modified for ARM64)
# This script supports ARM64

# Interrupt handler function
handle_interrupt() {
    echo ""
    echo "Installation interrupted by user (Ctrl+C or Esc)"
    echo "To reinstall, please run the script again"
    exit 1
}

# Setup signal trap for Ctrl+C
trap handle_interrupt SIGINT

# Save terminal settings and configure for immediate key reading
old_stty_settings=$(stty -g)
stty -icanon -echo min 1 time 0

# Background process to detect ESC key to interrupt the script
(while true; do
    read -r key
    if [[ $key == $'\e' ]]; then
        kill -SIGINT $$
        break
    fi
done) &

# Restore terminal settings on script exit
trap 'stty "$old_stty_settings"' EXIT

# Print banner in green
echo -e "\e[1;32m"
cat << "EOF"
Author: Huynh (ARM64 version)
     _    ____  __  __ 
    / \  |  _ \|  \/  |
   / _ \ | |_) | |\/| |
  / ___ \|  _ <| |  | |
 /_/   \_\_| \_\_|  |_|
EOF
echo -e "\e[0m"
echo -e "\e[1;36m One-click installer for XiaoZhi Server on ARM64 \e[0m\n"
sleep 1

# Check root permission
if [ $EUID -ne 0 ]; then
    echo "Please run this script as root"
    exit 1
fi

# Check OS version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] && [ "$ID" != "ubuntu" ]; then
        echo "This script only supports Debian/Ubuntu systems"
        exit 1
    fi
else
    echo "Cannot determine OS version, only Debian/Ubuntu supported"
    exit 1
fi

# Install whiptail if not installed
if ! command -v whiptail &>/dev/null; then
    echo "Installing whiptail..."
    apt update
    apt install -y whiptail
fi

# Install curl if not installed
if ! command -v curl &>/dev/null; then
    echo "Installing curl..."
    apt update
    apt install -y curl
fi

# Install Docker if not installed
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    DISTRO=$(lsb_release -cs)
    MIRROR_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    GPG_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"

    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_URL" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $MIRROR_URL $DISTRO stable" > /etc/apt/sources.list.d/docker.list
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7EA0A9C3F273FCD8 2>/dev/null || echo "Warning: some keys failed to add"
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    systemctl start docker
    systemctl enable docker
    docker --version || { echo "Docker installation failed"; exit 1; }
else
    echo "Docker is already installed"
fi

# Create necessary directories
mkdir -p /opt/xiaozhi-server/data
mkdir -p /opt/xiaozhi-server/models/SenseVoiceSmall

# Download voice recognition model
MODEL_PATH="/opt/xiaozhi-server/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PATH" ]; then
    echo "Downloading voice recognition model..."
    curl -fL --progress-bar https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt -o "$MODEL_PATH" || { echo "Failed to download model"; exit 1; }
else
    echo "Model already exists, skipping download"
fi

# Download docker-compose_arm.yml
COMPOSE_FILE="/opt/xiaozhi-server/docker-compose_arm.yml"
COMPOSE_URL="https://raw.githubusercontent.com/HuYingTran/xiaozhi-esp32-server/main/xiaozhi-server/docker-compose_arm.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Downloading docker-compose_arm.yml..."
    curl -fL --progress-bar "$COMPOSE_URL" -o "$COMPOSE_FILE" || { echo "Failed to download docker-compose_arm.yml"; exit 1; }
else
    echo "docker-compose_arm.yml already exists, skipping download"
fi

# --- Download additional Dockerfiles ---
DOCKERFILES_DIR="/opt/xiaozhi-server"
BASE_URL="https://raw.githubusercontent.com/HuYingTran/xiaozhi-esp32-server/main/xiaozhi-server"

for FILE in Dockerfile-server-base Dockerfile-server-arm Dockerfile-web; do
    TARGET_PATH="$DOCKERFILES_DIR/$FILE"
    FILE_URL="$BASE_URL/$FILE"
    if [ ! -f "$TARGET_PATH" ]; then
        echo "Downloading $FILE..."
        curl -fL --progress-bar "$FILE_URL" -o "$TARGET_PATH" || { echo "Failed to download $FILE"; exit 1; }
    else
        echo "$FILE already exists, skipping download"
    fi
done
# ---------------------------------------

# Change directory and build Docker images locally
cd /opt/xiaozhi-server || exit 1
echo "Building Docker images, this may take 10-30 minutes, please wait..."
docker compose -f docker-compose_arm.yml build || { echo "Docker image build failed"; exit 1; }

# Start Docker containers
docker compose -f docker-compose_arm.yml up -d || { echo "Failed to start Docker containers"; exit 1; }

# Show final info
LOCAL_IP=$(hostname -I | awk '{print $1}')
whiptail --title "Installation Complete" --msgbox "Server installation complete! Access addresses:\n\nAdmin Panel: http://$LOCAL_IP:8002\nOTA URL: http://$LOCAL_IP:8002/xiaozhi/ota/\nVision Analysis API: http://$LOCAL_IP:8003/mcp/vision/explain\nWebSocket: ws://$LOCAL_IP:8000/xiaozhi/v1/\n\nThank you for using!" 16 70
