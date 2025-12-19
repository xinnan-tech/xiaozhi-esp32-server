docker run --restart=on-failure:3 \
    --gpus all \
    -d \
    -p 18000:18000 \
    -v /home/ubuntu/.cache/huggingface:/root/.cache/huggingface \
    --name turn_detect \
    turn_det:latest

