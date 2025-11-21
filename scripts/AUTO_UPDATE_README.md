# 小智服务端自动更新使用指南

本文档介绍如何使用自动更新脚本保持小智服务端始终运行最新版本。

## 📋 文件说明

| 文件                   | 功能             | 使用场景       |
| ---------------------- | ---------------- | -------------- |
| `docker-setup.sh`      | 首次完整安装     | 全新服务器部署 |
| `auto-update.sh`       | 自动更新脚本     | 日常更新维护   |
| `setup-auto-update.sh` | 一键配置自动更新 | 配置定时任务   |
| `manage.sh`            | 服务管理脚本     | 日常运维管理   |

---

## 🚀 快速开始

### 第一次部署（全新服务器）

```bash
# 1. 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/BladeRunner18/xiaozhi-esp32-server/main/docker-setup.sh | bash

# 2. 配置自动更新
curl -fsSL https://raw.githubusercontent.com/BladeRunner18/xiaozhi-esp32-server/main/setup-auto-update.sh | bash

# 完成！服务将自动保持最新
```

---

## 🔄 配置自动更新（已部署服务器）

如果你已经运行了 `docker-setup.sh`，现在想要配置自动更新：

```bash
# 方式 1：使用一键配置脚本（推荐）
cd /opt/xiaozhi-server
curl -O https://raw.githubusercontent.com/BladeRunner18/xiaozhi-esp32-server/main/setup-auto-update.sh
sudo bash setup-auto-update.sh

# 方式 2：手动配置
cd /opt/xiaozhi-server
curl -O https://raw.githubusercontent.com/BladeRunner18/xiaozhi-esp32-server/main/auto-update.sh
chmod +x auto-update.sh

# 添加定时任务（每天凌晨 2 点）
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/xiaozhi-server/auto-update.sh") | crontab -
```

---

## 📖 详细使用说明

### 1. 手动更新

```bash
# 立即执行更新
/opt/xiaozhi-server/auto-update.sh

# 或使用管理脚本
/opt/xiaozhi-server/manage.sh update
```

### 2. 查看更新日志

```bash
# 实时查看日志
tail -f /opt/xiaozhi-server/logs/auto-update.log

# 查看最近 50 行
tail -n 50 /opt/xiaozhi-server/logs/auto-update.log

# 搜索错误日志
grep ERROR /opt/xiaozhi-server/logs/auto-update.log
```

### 3. 定时任务管理

```bash
# 查看当前定时任务
crontab -l

# 编辑定时任务
crontab -e

# 删除自动更新定时任务
crontab -l | grep -v "auto-update.sh" | crontab -
```

### 4. 服务状态检查

```bash
# 查看服务状态
/opt/xiaozhi-server/manage.sh status

# 或直接使用 docker-compose
cd /opt/xiaozhi-server
docker compose -f docker-compose_all.yml ps
```

---

## ⚙️ 自动更新脚本功能

`auto-update.sh` 脚本会自动执行以下操作：

1. ✅ **环境检查**：验证 Docker 和项目配置
2. ✅ **拉取镜像**：从 GHCR 拉取最新镜像
3. ✅ **检测更新**：对比镜像 ID，判断是否有新版本
4. ✅ **备份状态**：保存当前服务状态到 backup 目录
5. ✅ **滚动更新**：使用零停机部署策略更新服务
6. ✅ **健康检查**：等待并验证服务启动成功
7. ✅ **清理镜像**：删除悬空和未使用的旧镜像
8. ✅ **记录日志**：详细记录每次更新过程

---

## 📅 推荐的定时更新频率

| 场景         | 推荐频率      | Cron 表达式   |
| ------------ | ------------- | ------------- |
| **生产环境** | 每天凌晨 2 点 | `0 2 * * *`   |
| **测试环境** | 每 6 小时     | `0 */6 * * *` |
| **开发环境** | 每小时        | `0 * * * *`   |
| **稳定优先** | 每周日凌晨    | `0 2 * * 0`   |

---

## 🔍 故障排查

### 问题 1：更新失败，无法拉取镜像

**原因**：网络问题或镜像不存在

**解决方案**：

```bash
# 1. 检查网络连接
ping ghcr.io

# 2. 检查镜像是否存在且为公开
docker pull ghcr.nju.edu.cn/BladeRunner18/xiaozhi-esp32-server:server_latest

# 3. 如果是私有镜像，需要登录
docker login ghcr.io -u BladeRunner18
```

### 问题 2：服务更新后无法启动

**原因**：配置不兼容或数据库迁移失败

**解决方案**：

```bash
# 1. 查看服务日志
docker logs xiaozhi-esp32-server
docker logs xiaozhi-esp32-server-web

# 2. 检查数据库状态
docker exec -it xiaozhi-esp32-server-db mysql -uroot -p123456

# 3. 如果需要回滚，恢复旧镜像
docker tag <旧镜像ID> ghcr.nju.edu.cn/BladeRunner18/xiaozhi-esp32-server:server_latest
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
```

### 问题 3：定时任务不执行

**原因**：crontab 配置错误或权限问题

**解决方案**：

```bash
# 1. 检查 crontab 日志
grep CRON /var/log/syslog

# 2. 确认脚本有执行权限
ls -l /opt/xiaozhi-server/auto-update.sh

# 3. 手动测试脚本
sudo /opt/xiaozhi-server/auto-update.sh

# 4. 检查 crontab 配置
crontab -l
```

---

## 🎯 最佳实践

### 1. 定期备份数据

```bash
# 备份数据库
docker exec xiaozhi-esp32-server-db mysqldump -uroot -p123456 xiaozhi_esp32_server > backup.sql

# 备份配置文件
tar -czf config-backup.tar.gz /opt/xiaozhi-server/data/
```

### 2. 监控更新日志

```bash
# 设置日志告警（可选）
# 当日志中出现 ERROR 时发送邮件
grep ERROR /opt/xiaozhi-server/logs/auto-update.log | mail -s "小智更新失败" your@email.com
```

### 3. 测试更新流程

```bash
# 在生产环境应用前，先在测试环境验证
# 1. 拉取最新代码
git pull origin main

# 2. 在测试服务器运行更新
ssh test-server "/opt/xiaozhi-server/auto-update.sh"

# 3. 验证功能正常后，再应用到生产
```

---

## 📚 相关文档

- [Docker 部署文档](docs/Deployment_all.md)
- [源码部署文档](docs/dev-ops-integration.md)
- [项目主 README](README.md)

---

## 💬 获取帮助

如果遇到问题：

1. 查看日志：`tail -f /opt/xiaozhi-server/logs/auto-update.log`
2. 检查 Issues：[GitHub Issues](https://github.com/BladeRunner18/xiaozhi-esp32-server/issues)
3. 查看原项目：[xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)

---

## 📄 许可证

继承原项目许可证。详见 [LICENSE](LICENSE) 文件。
