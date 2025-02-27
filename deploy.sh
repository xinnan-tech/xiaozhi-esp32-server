#!/bin/bash
set -x
set -e

COMPOSE_DIR='compose-config'
server_no=$(ifconfig  eno1 | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F. '{print $4}')
compose_file="${COMPOSE_DIR}/${APP_ENV}-${server_no}-docker-compose.yml"
#判断compose_file是否存在，如果不存在echo后-退出-说明
if [ ! -f "$compose_file" ]; then
    echo "Error: Compose file '$compose_file' not found. Exiting."
    exit 1
fi
echo "Exute compose file: '$compose_file'."

echo "git pull"
git pull

docker compose -f ${compose_file} up -d --build

sleep 3
docker logs -f -n 30 esp32-server