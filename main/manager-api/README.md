本文档是开发类文档，如需部署小智服务端，[点击这里查看部署教程](.././FAQ.md#%E4%BD%BF%E7%94%A8%E6%96%B9%E5%BC%8F-)
# 项目介绍

manager-api 该项目基于SpringBoot框架开发。

开发使用代码编辑器，导入项目时，选择`manager-api`文件夹作为项目目录

# 开发环境
JDK 21
Maven 3.8+
MySQL 8.0+
Redis 5.0+
Vue 3.x

# 创建数据库

如果本机已经安装了MySQL，可以直接在数据库中创建名为`xiaozhi_esp32_server`的数据库。

```sql
CREATE DATABASE xiaozhi_esp32_server CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

如果还没有MySQL，你可以通过docker安装mysql

```
docker run --name xiaozhi-esp32-server-db \
-e MYSQL_ROOT_PASSWORD=123456 \
-p 3306:3306 \
-e MYSQL_DATABASE=xiaozhi_esp32_server \
-e MYSQL_INITDB_ARGS="--character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci" \
-d mysql:latest
```

# 确认项目数据库连接信息

在`src/main/resources/application-dev.yml`中配置数据库连接信息

```
spring:
  datasource:
    username: root
    password: 123456
```


# 连接Redis

如果还没有Redis，你可以通过docker安装redis

```
docker run --name xiaozhi-esp32-server-redis -d -p 6379:6379 redis
```

# 确认项目Redis连接信息

在`src/main/resources/application-dev.yml`中配置Redis连接信息

```
spring:
    data:
      redis:
        host: localhost
        port: 6379
        password:
        database: 0
```


# 测试启动

本项目为SpringBoot项目，启动方式为：
打开`Application.java`运行`Main`方法启动

```
路径地址：
src/main/java/xiaozhi/AdminApplication.java
```

# 打包编译

执行以下命令生产jar包

```
mvn clean install
```

把jar包放在服务器上，执行

```
nohup java -jar xiaozhi-esp32-api.jar --spring.profiles.activate=dev
```


# 接口文档
启动后打开：http://localhost:8002/xiaozhi-esp32-api/doc.html

