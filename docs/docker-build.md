# 编译docker镜像
> 两个Dockerfile 可以自行根据网络条件选择

## 使用Dockerfile编译镜像
1、安装docker（国内）
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2、编译docker镜像
```
# 普通编译
docker build -t xiaozhi-esp32-server:local -f ./Docker/Dockerfile .
```
3、测试本地镜像
```
docker stop xiaozhi-esp32-server
docker rm xiaozhi-esp32-server

docker run -d --name xiaozhi-esp32-server --restart always -p 8000:8000 -v $(pwd)/data/.config.yaml:/opt/xiaozhi-esp32-server/config.yaml xiaozhi-esp32-server:local

docker logs -f xiaozhi-esp32-server

```
5、发布腾讯云镜像
```
# amd64
docker tag xiaozhi-esp32-server:local ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-amd64
docker push ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-amd64

# arm64
docker tag xiaozhi-esp32-server:local ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-arm64
docker push ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-arm64

# 推送最新版本
docker manifest rm ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
docker manifest create ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-amd64 ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest-arm64 --amend
docker manifest inspect ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
docker manifest push ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest

```
6、运行线上镜像
```
cd /Users/hrz/myworkspace/docker-java-env/thirddata/
docker run -d --name xiaozhi-esp32-server --restart always -p 8000:8000 -v $(pwd)/config.yaml:/opt/xiaozhi-esp32-server/config.yaml ccr.ccs.tencentyun.com/xinnan/xiaozhi-esp32-server:latest
docker logs -f xiaozhi-esp32-server
```

## 使用Dockerfile-pip编译镜像 (代理)

1、复制并编译config.yaml
```
cp config.yaml ./data/.config.yaml
```
2、运行编译命令
```
docker build -t xiaozhi-esp32-server -f ./Docker/Dockerfile-pip .
```
3、运行线上镜像
```
docker run -d --name xiaozhi-esp32-server --restart always -p 8000:8000 -p 8002:8002 -v $(pwd)/data:/opt/xiaozhi-esp32-server/data xiaozhi-esp32-server
``` 
4、查看日志
```
docker logs -f xiaozhi-esp32-server
```