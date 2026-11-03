本文档是开发类文档，如需部署小智服务端，[点击这里查看部署教程](../../README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3)

# 项目介绍

manager-api 该项目基于SpringBoot框架开发。

开发使用代码编辑器，导入项目时，选择`manager-api`文件夹作为项目目录

# 开发环境
JDK 21
Maven 3.8+
MySQL 8.0+
Redis 5.0+
Vue 3.x

# 接口文档
启动后打开：http://localhost:8002/xiaozhi/doc.html

# 跑测试
测试分两种：纯单元测试，和要真连 MySQL、Redis 的集成测试（`DeviceTest`、`loginControllerTest`、`ModelConfigPersistenceTest`）。

集成测试需要先起好 MySQL 8 和 Redis 8。没起的时候这类测试整类跳过，不会让构建变红，日志里会写明缺的是哪个依赖。CI 上不一样：依赖连不上就直接让构建失败，不许跳过，免得门禁被悄悄掏空。

本地用 Docker 起这两个依赖：

```bash
docker run -d --name xiaozhi-mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 -e MYSQL_DATABASE=xiaozhi_esp32_server mysql:8.0
docker run -d --name xiaozhi-redis -p 6379:6379 redis:8.0
```

跑全部测试：

```bash
mvn -B test -DskipTests=false
```

只想编译、不跑测试：

```bash
mvn -B package -DskipTests=true
```

