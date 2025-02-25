## 构建镜像
```shell
docker build \
    --build-arg HTTP_PROXY=http://192.168.101.241:7890 \
    --build-arg HTTPS_PROXY=http://192.168.101.241:7890 \
    -f Dockerfile ./ \
    -t 192.168.101.99/yyn/192.168.101.99/yyn/esp32-server:1.0
```