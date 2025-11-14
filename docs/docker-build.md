# 本地编译docker镜像方法

## 1、快速开始 (Quick Start)  
 下载源码（arm 分支
 ```
git clone -b arm https://github.com/HuYingTran/xiaozhi-esp32-server.git
```
```
cd xiaozhi-esp32-server
```
使用 root 权限执行自动化安装脚本（包括依赖、Docker 构建
```
sudo bash docker-setup-arm.sh
```

## 2、现在本项目已经使用github自动编译docker功能，本文档是提供给有本地编译docker镜像需求的朋友准备的。

2.1、安装docker
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2.2、编译docker镜像
```
#进入项目根目录
# 编译server
docker build -t xiaozhi-esp32-server:server_latest -f ./Dockerfile-server .
# 编译web
docker build -t xiaozhi-esp32-server:web_latest -f ./Dockerfile-web .

# 编译完成后，可以使用docker-compose启动项目
# docker-compose.yml你需要修改成自己编译的镜像版本
cd main/xiaozhi-server
docker compose up -d
```
