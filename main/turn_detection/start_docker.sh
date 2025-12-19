docker run --restart=on-failure:3 \
    --gpus all \
    -itd \
    -p 8002:18000 \
    -v /data/yangxianjie/TEN_Turn_Detection/:/data/yangxianjie/TEN_Turn_Detection/ \
    --name turn_detect \
    turn_det:latest

