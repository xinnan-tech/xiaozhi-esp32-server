# Local compilation docker image method

This project now uses GitHub's automatic compilation of Docker images. This document is provided for friends who need to compile Docker images locally.

1. Install Docker
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2. Compile Docker image
```
#Enter the project root directory
# Compile the server
docker build -t xiaozhi-esp32-server:server_latest -f ./Dockerfile-server .
# Compile web
docker build -t xiaozhi-esp32-server:web_latest -f ./Dockerfile-web .

# After compilation is complete, you can use docker-compose to start the project
# You need to modify docker-compose.yml to the image version you compiled yourself
cd main/xiaozhi-server
docker compose up -d
```
