本文档是开发类文档，如需部署小智服务端，[点击这里查看部署教程](../../README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3)

# 项目介绍

manager-api 该项目基于SpringBoot框架开发。

开发使用代码编辑器，导入项目时，选择`manager-api`文件夹作为项目目录

# 开发环境
JDK 21
Maven 3.8+
MySQL 8.0.19+（迁移脚本 202610231200.sql 用了 WITH ... UPDATE 改写，8.0.19 才有；低版本会整段回滚导致服务起不来）
Redis 5.0+
Vue 3.x

# 接口文档
启动后打开：http://localhost:8002/xiaozhi/doc.html

