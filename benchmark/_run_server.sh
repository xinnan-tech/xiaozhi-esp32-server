#!/bin/bash
# 在 main/xiaozhi-server 目录启 wk01 服务到 18000 端口
cd /home/claw/myworkspace/wk01/xiaozhi-esp32-server/main/xiaozhi-server
pkill -f 'python app.py' 2>/dev/null
sleep 1
rm -f /tmp/wk01_xiaozhi.log
nohup /home/claw/miniconda3/envs/xiaozhi-esp32-server/bin/python app.py > /tmp/wk01_xiaozhi.log 2>&1 &
echo "started pid=$!"
disown
