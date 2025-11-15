#!/bin/sh
# Script author @VanillaNahida
This file is for automatically downloading the files required for this project with one click and automatically creating the directory.
# Currently only supports x86 versions of Ubuntu; other systems have not been tested.

# Define interrupt handler function
handle_interrupt() {
    echo ""
    echo "Installation was interrupted by the user (Ctrl+C or Esc)"
    echo "To reinstall, please run the script again."
    exit 1
}

# Configure signal capture, handle Ctrl+C
trap handle_interrupt SIGINT

# Handling the Esc key
# Save terminal settings
old_stty_settings=$(stty -g)
# Configure the terminal to respond immediately without echoing.
stty -icanon -echo min 1 time 0

# Background process detection using the Esc key
(while true; do
    read -r key
    if [[ $key == $'\e' ]]; then
        # Esc key detected, interrupt handling triggered
        kill -SIGINT $$
        break
    be
done) &

# Restore terminal settings when the script ends
trap 'stty "$old_stty_settings"' EXIT


# Print Color Character Artwork
echo -e "\e[1;32m" # Set the color to bright green
cat << "EOF"
Script author: @Bilibili Vanilla-flavored Naxi Da Miao
 __      __            _  _  _            _   _         _      _      _        
 \ \    / /           (_)| || |          | \ | |       | |    (_)    | |       
  \ \  / /__ _  _ __   _ | || |  __ _    |  \| |  __ _ | |__   _   __| |  __ _ 
   \ \/ // _` || '_ \ | || || | / _` |   | . ` | / _` || '_ \ | | / _` | / _` |
    \  /| (_| || | | || || || || (_| |   | |\  || (_| || | | || || (_| || (_| |
     \/  \__,_||_| |_||_||_||_| \__,_|   |_| \_| \__,_||_| |_||_| \__,_| \__,_|                                                                                                                                                                                                                               
EOF
echo -e "\e[0m" # Reset colors
echo -e "\e[1;36m Xiaozhi Server Full Deployment One-Click Installation Script Ver 0.2 Updated August 20, 2025\e[0m\n"
sleep 1



# Check and install whiptail
check_whiptail() {
    if ! command -v whiptail &> /dev/null; then
        echo "Installing whiptail..."
        apt update
        apt install -y whiptail
    be
}

check_whiptail

# Create a confirmation dialog box
whiptail --title "Installation Confirmed" --yesno "Xiaozhi server is about to be installed, continue?"
  --yes-button "Continue" --no-button "Exit" 10 50

# Perform the operation based on the user's selection.
case $? in
  0)
    ;;
  1)
    exit 1
    ;;
esac

# Check root privileges
if [ $EUID -ne 0 ]; then
    whiptail --title "Permission error" --msgbox "Please run this script with root privileges" 10 50
    exit 1
be

# Check system version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] && [ "$ID" != "ubuntu" ]; then
        whiptail --title "System Error" --msgbox "This script only supports Debian/Ubuntu systems" 10 60
        exit 1
    be
else
    whiptail --title "System Error" --msgbox "Unable to determine system version. This script only supports Debian/Ubuntu systems" 10 60
    exit 1
be

# Download configuration file function
check_and_download() {
    local filepath=$1
    local url=$2
    if [ ! -f "$filepath" ]; then
        if ! curl -fL --progress-bar "$url" -o "$filepath"; then
            whiptail --title "Error" --msgbox "Download of file ${filepath} failed" 10 50
            exit 1
        be
    else
        echo "The file ${filepath} already exists; skip downloading."
    be
}

# Check if it is installed
check_installed() {
    # Check if the directory exists and is not empty
    if [ -d "/opt/xiaozhi-server/" ] && [ "$(ls -A /opt/xiaozhi-server/)" ]; then
        DIR_CHECK=1
    else
        DIR_CHECK=0
    be
    
    # Check if the container exists
    if docker inspect xiaozhi-esp32-server > /dev/null 2>&1; then
        CONTAINER_CHECK=1
    else
        CONTAINER_CHECK=0
    be
    
    # Both checks passed
    if [ $DIR_CHECK -eq 1 ] && [ $CONTAINER_CHECK -eq 1 ]; then
        return 0 # Installed
    else
        return 1 # Not installed
    be
}

# Update related
if check_installed; then
    If whiptail --title "Installation Detection" --yesno "Xiaozhi server detected, upgrade?" 10 60; then
        # The user selects to upgrade and performs a cleanup operation.
        echo "Initiating upgrade operation..."
        
        # Stop and remove all docker-compose services
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down
        
        # Stop and delete a specific container (considering the possibility that the container may not exist).
        containers=(
            "xiaozhi-esp32-server"
            "xiaozhi-esp32-server-web"
            "xiaozhi-esp32-server-db
            "xiaozhi-esp32-server-redis"
        )
        
        for container in "${containers[@]}"; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                docker stop "$container" >/dev/null 2>&1 && \
                docker rm "$container" >/dev/null 2>&1 && \
                echo "Container successfully removed: $container"
            else
                echo "Container does not exist, skip: $container"
            be
        done
        
        # Delete a specific image (considering the possibility that the image may not exist).
        images=(
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest"
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:web_latest"
        )
        
        for image in "${images[@]}"; do
            if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${image}$"; then
                docker rmi "$image" >/dev/null 2>&1 && \
                echo "Mirror image successfully deleted: $image"
            else
                echo "Image does not exist, skip: $image"
            be
        done
        
        echo "All cleanup operations completed"
        
        # Backup existing configuration files
        mkdir -p /opt/xiaozhi-server/backup/
        if [ -f /opt/xiaozhi-server/data/.config.yaml ]; then
            cp /opt/xiaozhi-server/data/.config.yaml /opt/xiaozhi-server/backup/.config.yaml
            echo "The original configuration file has been backed up to /opt/xiaozhi-server/backup/.config.yaml"
        be
        
        # Download the latest configuration file
        check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
        check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
        
        # Start Docker service
        echo "Starting the latest version service..."
        # Mark the page after the upgrade is complete to skip subsequent download steps.
        UPGRADE_COMPLETED=1
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    else
          whiptail --title "Skip upgrade" --msgbox "Upgrade canceled, will continue using the current version." 10 50
          # Skip the upgrade and continue with the subsequent installation process.
    be
be


# Check curl installation
if ! command -v curl &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "curl not detected, installing..."
    apt update
    apt install -y curl
else
    echo "------------------------------------------------------------"
    echo "curl is already installed, skip the installation steps"
be

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "Docker not detected, installing..."
    
    # Use a domestic mirror source instead of the official source
    DISTRO=$(lsb_release -cs)
    MIRROR_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    GPG_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"
    
    # Install basic dependencies
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    
    # Create a key directory and add domestic mirror source keys
    mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_URL" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Add domestic mirror source
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $MIRROR_URL $DISTRO stable" \
        > /etc/apt/sources.list.d/docker.list
    
    # Add a backup official source key (to avoid verification failures using domestic source keys)
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7EA0A9C3F273FCD8 2>/dev/null || \
    echo "Warning: Partial key addition failed, continue trying to install..."
    
    # Install Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    
    # Start service
    systemctl start docker
    systemctl enable docker
    
    # Check if the installation was successful
    if docker --version; then
        echo "------------------------------------------------------------"
        echo "Docker installation complete!"
    else
        whiptail --title "Error" --msgbox "Docker installation failed, please check the logs." 10 50
        exit 1
    be
else
    echo "Docker is already installed, skip the installation steps"
be

# Docker image source configuration
MIRROR_OPTIONS=(
    "1" "Xuanyuan Mirror (Recommended)"
    "2" "Tencent Cloud Mirror Source"
    "3" "USTC Mirror Source"
    "4" "NetEase 163 Mirror Source"
    "5" "Huawei Cloud Mirror Source"
    "6" "Alibaba Cloud Mirror Source"
    "7" "Custom Mirror Source"
    "8" "Skip Configuration"
)

MIRROR_CHOICE=$(whiptail --title "Select Docker image source" --menu "Please select the Docker image source to use" 20 60 10 \
"${MIRROR_OPTIONS[@]}" 3>&1 1>&2 2>&3) || {
    echo "User canceled selection, exit script"
    exit 1
}

case $MIRROR_CHOICE in
    1) MIRROR_URL="https://docker.xuanyuan.me" ;; 
    2) MIRROR_URL="https://mirror.ccs.tencentyun.com" ;; 
    3) MIRROR_URL="https://docker.mirrors.ustc.edu.cn" ;; 
    4) MIRROR_URL="https://hub-mirror.c.163.com" ;; 
    5) MIRROR_URL="https://05f073ad3c0010ea0f4bc00b7105ec20.mirror.swr.myhuaweicloud.com" ;; 
    6) MIRROR_URL="https://registry.aliyuncs.com" ;; 
    7) MIRROR_URL=$(whiptail --title "Custom Mirror Source" --inputbox "Please enter the complete mirror source URL:" 10 60 3>&1 1>&2 2>&3) ;;
    8) MIRROR_URL="" ;; 
esac

if [ -n "$MIRROR_URL" ]; then
    mkdir -p /etc/docker
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    be
    cat > /etc/docker/daemon.json <<EOF
{
    "dns": ["8.8.8.8", "114.114.114.114"],
    "registry-mirrors": ["$MIRROR_URL"]
}
EOF
    whiptail --title "Configuration successful" --msgbox "Image source added successfully: $MIRROR_URL\nPlease press Enter to restart the Docker service and continue..." 12 60
    echo "------------------------------------------------------------"
    echo "Starting to restart Docker service..."
    systemctl restart docker.service
be

# Create installation directory
echo "------------------------------------------------------------"
echo "Starting to create installation directory..."
# Check and create the data directory
if [ ! -d /opt/xiaozhi-server/data ]; then
    mkdir -p /opt/xiaozhi-server/data
    echo "Data directory created: /opt/xiaozhi-server/data"
else
    echo "Directory xiaozhi-server/data already exists, skip creation"
be

# Check and create the model catalog
if [ ! -d /opt/xiaozhi-server/models/SenseVoiceSmall ]; then
    mkdir -p /opt/xiaozhi-server/models/SenseVoiceSmall
    echo "Model directory created: /opt/xiaozhi-server/models/SenseVoiceSmall"
else
    echo "Directory xiaozhi-server/models/SenseVoiceSmall already exists, skipping creation"
be

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
    ) | whiptail --title "Downloading" --gauge "Starting to download speech recognition model..." 10 60 0
    curl -fL --progress-bar https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt -o "$MODEL_PATH" || {
        whiptail --title "Error" --msgbox "Failed to download model.pt file" 10 50
        exit 1
    }
else
    echo "model.pt file already exists, skip downloading"
be

# Download will only proceed if the upgrade is not complete.
if [ -z "$UPGRADE_COMPLETED" ]; then
    check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
    check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
be

# Start Docker service
(
echo "------------------------------------------------------------"
echo "Pulling Docker image..."
This may take a few minutes, please wait patiently.
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d

if [ $? -ne 0 ]; then
    whiptail --title "Error" --msgbox "Docker service failed to start. Please try changing the image source and re-execute this script." 10 60
    exit 1
be

echo "------------------------------------------------------------"
echo "Checking service startup status..."
TIMEOUT=300
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $TIMEOUT ]; then
        whiptail --title "Error" --msgbox "Service startup timed out, expected log content not found within the specified time" 10 60
        exit 1
    be
    
    if docker logs xiaozhi-esp32-server-web 2>&1 | grep -q "Started AdminApplication in"; then
        break
    be
    sleep 1
done

    echo "Server started successfully! Completing configuration..."
    echo "Starting service..."
    docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    echo "Service startup complete!"
)

# Key Configuration

# Get the server's public IP address
PUBLIC_IP=$(hostname -I | awk '{print $1}')
whiptail --title "Configure Server Key" --msgbox "Please use a browser to access the link below, open the smart console, and register an account:\n\nInternal network address: http://127.0.0.1:8002/\nPublic network address: http://$PUBLIC_IP:8002/ (If it is a cloud server, please allow ports 8000, 8001, and 8002 in the server security group).\n\nThe first user registered is the super administrator; subsequent users are ordinary users. Ordinary users can only bind devices and configure smart agents; super administrators can perform model management, user management, parameter configuration, and other functions.\n\nPlease press Enter to continue after registration." 18 70
SECRET_KEY=$(whiptail --title "Configure Server Key" --inputbox "Please log in to the smart console using the super administrator account\nInternal network address: http://127.0.0.1:8002/\nPublic network address: http://$PUBLIC_IP:8002/\nFind the parameter code: server.secret (server key) in the top menu Parameter Dictionary → Parameter Management\nCopy this parameter value and enter it into the input box below\n\nPlease enter the key (leave blank to skip configuration):" 15 60 3>&1 1>&2 2>&3)

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
be

# Get and display address information
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Fixed the issue of not being able to retrieve the ws file from the log file; changed it to hard encoding.
whiptail --title "Installation complete!" --msgbox "\
The server-side address is as follows:\n\
Admin panel access address: http://$LOCAL_IP:8002\n\
OTA Location: http://$LOCAL_IP:8002/xiaozhi/ota/\n\
Visual analytics interface address: http://$LOCAL_IP:8003/mcp/vision/explain\n\
WebSocket address: ws://$LOCAL_IP:8000/xiaozhi/v1/\n\
Installation complete! Thank you for using our service! Press Enter to exit... 16 70