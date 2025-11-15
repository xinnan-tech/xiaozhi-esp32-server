#!/bin/sh
# Script by @VanillaNahida
# This file is used to automatically download the files required for this project with one click and automatically create a directory.
# For the time being, only the X86 version of Ubuntu system is supported, and other systems have not been tested.e X86 version of Ubuntu system is supported, and other systems have not been tested.

# Define interrupt handler function
handle_interrupt() {
    echo ""
    echo "The installation has been interrupted by the user (ctrl+c or esc)"
    echo "To reinstall, run the script again"
    exit 1
}

# Set signal capture, handle ctrl+c
trap handle_interrupt SIGINT

# Handling the Esc key
# Save terminal settings
old_stty_settings=$(stty -g)
# Set the terminal to respond immediately without echoing
stty -icanon -echo min 1 time 0

# Background process detects esc key
(while true; do
    read -r key
    if [[ $key == $'\e' ]]; then
        # The esc key is detected and interrupt processing is triggered.
        kill -SIGINT $$
        break
    fi
done) &

# Restore terminal settings when script ends
trap 'stty "$old_stty_settings"' EXIT


# Print colorful character paintings
echo -e "\e[1;32m"  # Set color to bright green
cat << "EOF"
脚本作者：@Bilibili 香草味的纳西妲喵
 __      __            _  _  _            _   _         _      _      _        
 \ \    / /           (_)| || |          | \ | |       | |    (_)    | |       
  \ \  / /__ _  _ __   _ | || |  __ _    |  \| |  __ _ | |__   _   __| |  __ _ 
   \ \/ // _` || '_ \ | || || | / _` |   | . ` | / _` || '_ \ | | / _` | / _` |
    \  /| (_| || | | || || || || (_| |   | |\  || (_| || | | || || (_| || (_| |
     \/  \__,_||_| |_||_||_||_| \__,_|   |_| \_| \__,_||_| |_||_| \__,_| \__,_|                                                                                                                                                                                                                               
EOF
echo -e "\e[0m"  # reset color
echo -e "\e[1;36m Jahanshahlou server fully deploys one-click installation script Ver 0.2 updated on August 20, 2025 \e[0m\n"
sleep 1



# Check and install whiptail
check_whiptail() {
    if ! command -v whiptail &> /dev/null; then
        echo "Installing whiptail..."
        apt update
        apt install -y whiptail
    fi
}

check_whiptail

# Create confirmation dialog
whiptail --title "Installation confirmation" --yesno "Xiaozhi server is about to be installed. Do you want to continue?" \
  --yes-button "continue" --no-button "quit" 10 50

# Perform actions based on user selections
case $? in
  0)
    ;;
  1)
    exit 1
    ;;
esac

# Check root permissions
if [ $EUID -ne 0 ]; then
    whiptail --title "Permission error" --msgbox "Please use root privileges to run this script" 10 50
    exit 1
fi

# Check system version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] && [ "$ID" != "ubuntu" ]; then
        whiptail --title "System error" --msgbox "This script only supports execution on debian/ubuntu systems" 10 60
        exit 1
    fi
else
    whiptail --title "System error" --msgbox "The system version cannot be determined. This script only supports debian/ubuntu system execution." 10 60
    exit 1
fi

# Download configuration file function
check_and_download() {
    local filepath=$1
    local url=$2
    if [ ! -f "$filepath" ]; then
        if ! curl -fL --progress-bar "$url" -o "$filepath"; then
            whiptail --title "mistake" --msgbox "${filepath}File download failed" 10 50
            exit 1
        fi
    else
        echo "${filepath}File already exists, skip download"
    fi
}

# Check if it is installed
check_installed() {
    # Check if the directory exists and is not empty
    if [ -d "/opt/xiaozhi-server/" ] && [ "$(ls -A /opt/xiaozhi-server/)" ]; then
        DIR_CHECK=1
    else
        DIR_CHECK=0
    fi
    
    # Check if the container exists
    if docker inspect xiaozhi-esp32-server > /dev/null 2>&1; then
        CONTAINER_CHECK=1
    else
        CONTAINER_CHECK=0
    fi
    
    # Passed both inspections
    if [ $DIR_CHECK -eq 1 ] && [ $CONTAINER_CHECK -eq 1 ]; then
        return 0  # Installed
    else
        return 1  # Not installed
    fi
}

# Update related
if check_installed; then
    if whiptail --title "Detection installed" --yesno "It is detected that the Xiaozhi server has been installed. Do you want to upgrade it?" 10 60; then
        # The user chooses to upgrade and perform a cleanup operation
        echo "Start the upgrade operation..."
        
        #Stop and remove all docker compose services
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down
        
        # Stop and delete a specific container (considering the case where the container may not exist)
        containers=(
            "xiaozhi-esp32-server"
            "xiaozhi-esp32-server-web"
            "xiaozhi-esp32-server-db"
            "xiaozhi-esp32-server-redis"
        )
        
        for container in "${containers[@]}"; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                docker stop "$container" >/dev/null 2>&1 && \
                docker rm "$container" >/dev/null 2>&1 && \
                echo "Container removed successfully: $container"
            else
                echo "Container does not exist, skip: $container"
            fi
        done
        
        # Delete a specific image (consider that the image may not exist)
        images=(
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest"
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:web_latest"
        )
        
        for image in "${images[@]}"; do
            if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${image}$"; then
                docker rmi "$image" >/dev/null 2>&1 && \
                echo "Image deleted successfully: $image"
            else
                echo "Mirror does not exist, skip: $image"
            fi
        done
        
        echo "All cleanup operations completed"
        
        # Back up original configuration files
        mkdir -p /opt/xiaozhi-server/backup/
        if [ -f /opt/xiaozhi-server/data/.config.yaml ]; then
            cp /opt/xiaozhi-server/data/.config.yaml /opt/xiaozhi-server/backup/.config.yaml
            echo "The original configuration file has been backed up to /opt/xiaozhi-server/backup/.config.yaml"
        fi
        
        # Download the latest configuration file
        check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
        check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
        
        # Start docker service
        echo "Start launching the latest version of the service..."
        # Mark after the upgrade is complete to skip subsequent download steps
        UPGRADE_COMPLETED=1
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    else
          whiptail --title "Skip upgrade" --msgbox "The upgrade has been canceled and the current version will continue to be used." 10 50
          # Skip the upgrade and continue with the subsequent installation process
    fi
fi


# Check curl installation
if ! command -v curl &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "curl not detected, installing..."
    apt update
    apt install -y curl
else
    echo "------------------------------------------------------------"
    echo "Curl is already installed, skip the installation steps"
fi

# Check docker installation
if ! command -v docker &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "docker not detected, installing..."
    
    # Use domestic mirror sources instead of official sources
    DISTRO=$(lsb_release -cs)
    MIRROR_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    GPG_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"
    
    # Install basic dependencies
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    
    # Create a key directory and add the domestic image source key
    mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_URL" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add domestic mirror source
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $MIRROR_URL $DISTRO stable" \
        > /etc/apt/sources.list.d/docker.list
    
    # Add alternate official source key (to avoid domestic source key verification failure)
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7EA0A9C3F273FCD8 2>/dev/null || \
    echo "Warning: Some keys failed to be added, continue to try to install..."
    
    # Install docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    
    # Start service
    systemctl start docker
    systemctl enable docker
    
    # Check if the installation is successful
    if docker --version; then
        echo "------------------------------------------------------------"
        echo "Docker installation is complete!"
    else
        whiptail --title "mistake" --msgbox "Docker installation failed, please check the logs." 10 50
        exit 1
    fi
else
    echo "Docker is already installed, skip the installation steps"
fi

# Docker image source configuration
MIRROR_OPTIONS=(
    "1" "Xuanyuan Mirror (recommended)"
    "2" "Tencent cloud mirror source"
    "3" "University of Science and Technology of China Mirror Source"
    "4" "NetEase 163 mirror source"
    "5" "Huawei Cloud Mirror Source"
    "6" "Alibaba Cloud Mirror Source"
    "7" "Custom image source"
    "8" "Skip configuration"
)

MIRROR_CHOICE=$(whiptail --title "Select docker image source" --menu "Please select the docker image source to use" 20 60 10 \
"${MIRROR_OPTIONS[@]}" 3>&1 1>&2 2>&3) || {
    echo "User cancels selection and exits script"
    exit 1
}

case $MIRROR_CHOICE in
    1) MIRROR_URL="https://docker.xuanyuan.me" ;; 
    2) MIRROR_URL="https://mirror.ccs.tencentyun.com" ;; 
    3) MIRROR_URL="https://docker.mirrors.ustc.edu.cn" ;; 
    4) MIRROR_URL="https://hub-mirror.c.163.com" ;; 
    5) MIRROR_URL="https://05f073ad3c0010ea0f4bc00b7105ec20.mirror.swr.myhuaweicloud.com" ;; 
    6) MIRROR_URL="https://registry.aliyuncs.com" ;; 
    7) MIRROR_URL=$(whiptail --title "Custom image source" --inputbox "Please enter the complete mirror source URL:" 10 60 3>&1 1>&2 2>&3) ;; 
    8) MIRROR_URL="" ;; 
esac

if [ -n "$MIRROR_URL" ]; then
    mkdir -p /etc/docker
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    fi
    cat > /etc/docker/daemon.json <<EOF
{
    "dns": ["8.8.8.8", "114.114.114.114"],
    "registry-mirrors": ["$MIRROR_URL"]
}
EOF
    whiptail --title "Configuration successful" --msgbox "Mirror source added successfully: $MIRROR_URL\NPlease press the enter key to restart the docker service and continue..." 12 60
    echo "------------------------------------------------------------"
    echo "Start restarting the docker service..."
    systemctl restart docker.service
fi

# Create installation directory
echo "------------------------------------------------------------"
echo "Start creating the installation directory..."
# Check and create data directory
if [ ! -d /opt/xiaozhi-server/data ]; then
    mkdir -p /opt/xiaozhi-server/data
    echo "Data directory created: /opt/xiaozhi-server/data"
else
    echo "The directory xiaozhi server/data already exists, skip creation."
fi

# Check and create model catalog
if [ ! -d /opt/xiaozhi-server/models/SenseVoiceSmall ]; then
    mkdir -p /opt/xiaozhi-server/models/SenseVoiceSmall
    echo "Model directory created: /opt/xiaozhi-server/models/SenseVoiceSmall"
else
    echo "The directory xiaozhi server/models/sense voice small already exists, skip creation"
fi

echo "------------------------------------------------------------"
echo "Start downloading speech recognition model"
# Download model file
MODEL_PATH="/opt/xiaozhi-server/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PATH" ]; then
    (
    for i in {1..20}; do
        echo $((i*5))
        sleep 0.5
    done
    ) | whiptail --title "Downloading" --gauge "Start downloading speech recognition model..." 10 60 0
    curl -fL --progress-bar https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt -o "$MODEL_PATH" || {
        whiptail --title "mistake" --msgbox "model.Pt file download failed" 10 50
        exit 1
    }
else
    echo "Model.pt file already exists, skip downloading"
fi

# If the upgrade is not completed, the download will be executed.
if [ -z "$UPGRADE_COMPLETED" ]; then
    check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
    check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
fi

# Start docker service
(
echo "------------------------------------------------------------"
echo "Pulling docker image..."
echo "This may take a few minutes, please be patient"
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d

if [ $? -ne 0 ]; then
    whiptail --title "mistake" --msgbox "The Docker service failed to start. Please try changing the image source and re-executing this script." 10 60
    exit 1
fi

echo "------------------------------------------------------------"
echo "Checking service startup status..."
TIMEOUT=300
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $TIMEOUT ]; then
        whiptail --title "mistake" --msgbox "The service startup timed out and the expected log content was not found within the specified time." 10 60
        exit 1
    fi
    
    if docker logs xiaozhi-esp32-server-web 2>&1 | grep -q "Started AdminApplication in"; then
        break
    fi
    sleep 1
done

    echo "The server started successfully! Completing configuration..."
    echo "Starting service..."
    docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    echo "Service startup is complete!"
)

# Key configuration

# Get the server public network address
PUBLIC_IP=$(hostname -I | awk '{print $1}')
whiptail --title "Configure server key" --msgbox "Please use a browser, visit the link below, open the smart console and register an account: \n\nIntranet address: http://127.0.0.1:8002/\nPublic address: http://$PUBLIC_IP:8002/(If it is a cloud server, please release port 8000 8001 8002 in the server security group). \n\nThe first registered user is the super administrator, and subsequent registered users are ordinary users. Ordinary users can only bind devices and configure agents; super administrators can perform model management, user management, parameter configuration and other functions. \n\nAfter registering, please press Enter to continue." 18 70
SECRET_KEY=$(whiptail --title "Configure server key" --inputbox "Please use the super administrator account to log in to the intelligent console\nIntranet address: http://127.0.0.1:8002/\nPublic network address: http://$PUBLIC_IP:8002/\nIn the top menu Parameter Dictionary → Parameter Management Find the parameter encoding: server.secret (server key) \nCopy the parameter value and enter it into the input box below\n\nPlease enter the secret key (leave it blank to skip the configuration):" 15 60 3>&1 1>&2 2>&3)

if [ -n "$SECRET_KEY" ]; then
    python3 -c "
import sys, yaml; 
config_path = '/opt/xiaozhi-server/data/.config.yaml'; 
with open(config_path, 'r') as f: 
    config = yaml.safe_load(f) or {}; 
config['manager-api'] = {'url': 'http://xiaozhi-esp32-server-web:8002/xiaozhi', 'secret': '$SECRET_KEY'}; 
with open(config_path, 'w') as f: 
    yaml.dump(config, f); 
"
    docker restart xiaozhi-esp32-server
fi

# Get and display address information
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Fixed the problem that the log file could not obtain ws and changed it to hard coding.
whiptail --title "The installation is complete!" --msgbox "\
The relevant addresses of the server are as follows:\n\
Management backend access address: http://$LOCAL_IP:8002\n\
OTA address: http://$LOCAL_IP:8002/xiaozhi/ota/\n\
Visual analysis interface address: http://$LOCAL_IP:8003/mcp/vision/explain\n\
WebSocket address: ws://$LOCAL_IP:8000/xiaozhi/v1/\n\
\nInstallation completed! Thank you for your use! \nPress enter to exit..." 16 70
