# 阿里云部署指南

本指南将帮助您在阿里云ECS上构建Docker镜像并部署小智服务端，使其可以通过公网访问。

## 前置要求

1. 阿里云ECS服务器（建议配置：2核4G以上，Ubuntu 20.04/22.04）
2. 已配置安全组规则（开放端口：8000, 8002, 8003）
3. 域名（可选，用于HTTPS访问）
4. 已安装Docker和Docker Compose

## 一、服务器准备

### 1.1 安装Docker和Docker Compose

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

# 启动Docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 配置Docker镜像加速（使用阿里云镜像）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://your-id.mirror.aliyuncs.com"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

> 注意：将 `your-id` 替换为您的阿里云容器镜像服务ID，可在[阿里云容器镜像服务](https://cr.console.aliyun.com/)获取。

### 1.2 配置安全组

在阿里云控制台配置ECS安全组，开放以下端口：

| 端口 | 协议 | 说明 |
|------|------|------|
| 8000 | TCP | WebSocket服务端口 |
| 8002 | TCP | 智控台Web访问端口 |
| 8003 | TCP | HTTP服务端口（OTA、视觉分析） |
| 22 | TCP | SSH（默认已开放） |

## 二、构建Docker镜像

### 2.1 克隆项目代码

```bash
# 在服务器上克隆项目
cd /opt
git clone https://github.com/xinnan-tech/xiaozhi-esp32-server.git
cd xiaozhi-esp32-server
```

### 2.2 构建基础镜像（Server Base）

```bash
# 构建server-base镜像
docker build -t xiaozhi-esp32-server:server-base -f Dockerfile-server-base .
```

### 2.3 构建Server镜像

```bash
# 构建server镜像
docker build -t xiaozhi-esp32-server:server_latest -f Dockerfile-server .
```

### 2.4 构建Web镜像（包含前端和Java后端）

```bash
# 构建web镜像（这个过程可能需要较长时间，因为需要编译Vue和Java）
docker build -t xiaozhi-esp32-server:web_latest -f Dockerfile-web .
```

### 2.5 验证镜像

```bash
# 查看构建的镜像
docker images | grep xiaozhi-esp32-server
```

应该看到三个镜像：
- `xiaozhi-esp32-server:server-base`
- `xiaozhi-esp32-server:server_latest`
- `xiaozhi-esp32-server:web_latest`

## 三、准备部署文件

### 3.1 创建部署目录

```bash
mkdir -p /opt/xiaozhi-server/{data,models/SenseVoiceSmall,uploadfile,mysql/data}
cd /opt/xiaozhi-server
```

### 3.2 下载配置文件

```bash
# 下载docker-compose配置文件
wget https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/docker-compose_all.yml

# 下载配置文件模板
wget https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/config_from_api.yaml -O data/.config.yaml
```

### 3.3 修改docker-compose配置

编辑 `docker-compose_all.yml`，将镜像名称改为本地构建的镜像：

```yaml
services:
  xiaozhi-esp32-server:
    # 使用本地构建的镜像
    image: xiaozhi-esp32-server:server_latest
    # 或者使用build方式（如果镜像在项目目录）
    # build:
    #   context: /opt/xiaozhi-esp32-server
    #   dockerfile: Dockerfile-server

  xiaozhi-esp32-server-web:
    # 使用本地构建的镜像
    image: xiaozhi-esp32-server:web_latest
    # 或者使用build方式
    # build:
    #   context: /opt/xiaozhi-esp32-server
    #   dockerfile: Dockerfile-web
```

### 3.4 下载语音识别模型

```bash
# 下载SenseVoiceSmall模型（约200MB）
cd /opt/xiaozhi-server/models/SenseVoiceSmall
wget https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt
```

## 四、启动服务

### 4.1 启动所有服务

```bash
cd /opt/xiaozhi-server
docker compose -f docker-compose_all.yml up -d
```

### 4.2 查看服务状态

```bash
# 查看容器状态
docker compose -f docker-compose_all.yml ps

# 查看日志
docker compose -f docker-compose_all.yml logs -f
```

### 4.3 等待服务启动

等待约1-2分钟，直到看到以下日志表示启动成功：

```bash
# 查看web服务日志
docker logs xiaozhi-esp32-server-web | grep "Started AdminApplication"

# 查看server服务日志
docker logs xiaozhi-esp32-server | grep "Websocket地址"
```

## 五、配置访问

### 5.1 获取服务器公网IP

```bash
# 查看公网IP
curl ifconfig.me
# 或者
hostname -I
```

### 5.2 访问智控台

在浏览器中访问：
```
http://您的公网IP:8002
```

### 5.3 注册管理员账号

1. 访问智控台后，注册第一个账号（自动成为超级管理员）
2. 登录后，进入"参数管理"，找到 `server.secret`，复制密钥值
3. 编辑配置文件：

```bash
nano /opt/xiaozhi-server/data/.config.yaml
```

添加或修改以下配置：

```yaml
manager-api:
  url: http://xiaozhi-esp32-server-web:8002/xiaozhi
  secret: 您复制的server.secret值
```

4. 重启server服务：

```bash
docker restart xiaozhi-esp32-server
```

### 5.4 配置WebSocket和OTA地址

在智控台的"参数管理"中配置：

- `server.websocket`: `ws://您的公网IP:8000/xiaozhi/v1/`
- `server.ota`: `http://您的公网IP:8002/xiaozhi/ota/`

## 六、配置域名和HTTPS（可选但推荐）

### 6.1 安装Nginx

```bash
sudo apt install nginx -y
```

### 6.2 配置Nginx反向代理

创建Nginx配置文件：

```bash
sudo nano /etc/nginx/sites-available/xiaozhi
```

添加以下配置：

```nginx
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com;  # 替换为您的域名
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;  # 替换为您的域名
    
    # SSL证书配置（使用Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 智控台前端
    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket代理
    location /xiaozhi/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
    
    # API接口
    location /xiaozhi/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # OTA接口
    location /xiaozhi/ota/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # 视觉分析接口
    location /mcp/vision/ {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 6.3 安装SSL证书（使用Let's Encrypt）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 6.4 启用Nginx配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/xiaozhi /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 6.5 更新配置中的地址

使用域名后，需要更新配置：

1. 在智控台"参数管理"中更新：
   - `server.websocket`: `wss://your-domain.com/xiaozhi/v1/`（注意是wss）
   - `server.ota`: `https://your-domain.com/xiaozhi/ota/`

2. 重启服务：
```bash
docker restart xiaozhi-esp32-server
```

## 七、常用管理命令

### 7.1 查看服务状态

```bash
# 查看所有容器
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml ps

# 查看日志
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml logs -f

# 查看特定服务日志
docker logs -f xiaozhi-esp32-server
docker logs -f xiaozhi-esp32-server-web
```

### 7.2 重启服务

```bash
# 重启所有服务
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml restart

# 重启特定服务
docker restart xiaozhi-esp32-server
docker restart xiaozhi-esp32-server-web
```

### 7.3 停止服务

```bash
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down
```

### 7.4 更新服务

```bash
# 1. 停止服务
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down

# 2. 拉取最新代码
cd /opt/xiaozhi-esp32-server
git pull

# 3. 重新构建镜像
docker build -t xiaozhi-esp32-server:server_latest -f Dockerfile-server .
docker build -t xiaozhi-esp32-server:web_latest -f Dockerfile-web .

# 4. 启动服务
cd /opt/xiaozhi-server
docker compose -f docker-compose_all.yml up -d
```

## 八、故障排查

### 8.1 服务无法启动

```bash
# 查看详细日志
docker logs xiaozhi-esp32-server-web
docker logs xiaozhi-esp32-server

# 检查端口占用
sudo netstat -tlnp | grep -E '8000|8002|8003'
```

### 8.2 无法访问智控台

1. 检查安全组是否开放8002端口
2. 检查防火墙：
```bash
sudo ufw status
sudo ufw allow 8002
```

3. 检查容器是否运行：
```bash
docker ps | grep xiaozhi
```

### 8.3 WebSocket连接失败

1. 检查8000端口是否开放
2. 检查Nginx配置（如果使用域名）
3. 查看server日志确认WebSocket地址

## 九、性能优化建议

1. **资源配置**：建议至少2核4G内存
2. **数据库优化**：可以调整MySQL配置以提高性能
3. **缓存优化**：Redis已包含，确保有足够内存
4. **日志管理**：定期清理Docker日志，避免磁盘占满

```bash
# 清理Docker日志
docker system prune -f
```

## 十、安全建议

1. **修改默认密码**：修改MySQL root密码
2. **使用HTTPS**：强烈建议配置SSL证书
3. **定期更新**：保持系统和Docker镜像更新
4. **备份数据**：定期备份数据库和配置文件

```bash
# 备份数据库
docker exec xiaozhi-esp32-server-db mysqldump -uroot -p123456 xiaozhi_esp32_server > backup.sql

# 备份配置文件
cp -r /opt/xiaozhi-server/data /opt/xiaozhi-server/backup-$(date +%Y%m%d)
```

## 完成

部署完成后，您可以通过以下地址访问：

- **智控台**：`http://您的公网IP:8002` 或 `https://your-domain.com`
- **WebSocket**：`ws://您的公网IP:8000/xiaozhi/v1/` 或 `wss://your-domain.com/xiaozhi/v1/`
- **OTA接口**：`http://您的公网IP:8002/xiaozhi/ota/` 或 `https://your-domain.com/xiaozhi/ota/`

如有问题，请查看日志或参考项目文档。


