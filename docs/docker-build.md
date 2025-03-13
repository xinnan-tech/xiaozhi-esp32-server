# 本地编译docker镜像方法

现在本项目已经使用github自动编译docker功能，本文档是提供给有本地编译docker镜像需求的朋友准备的。

1、安装docker
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2、编译docker镜像
```
#进入xiaozhi-server目录
cd main/xiaozhi-server/
# 普通编译
docker build -t xiaozhi-esp32-server:local -f ./Dockerfile-pip .
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