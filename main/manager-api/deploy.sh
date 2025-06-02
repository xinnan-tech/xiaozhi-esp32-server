#!/bin/bash

# xiaozhi-esp32-api 超简化部署脚本
# 按用户要求：JAR放到data目录，日志写到logs目录

set -e

# 配置变量
APP_NAME="xiaozhi-api"
APP_VERSION="0.0.1"
JAR_NAME="${APP_NAME}-${APP_VERSION}.jar"
APP_BASE="/projects/running-apps/xiaozhi-api"
JAR_DIR="${APP_BASE}/data"
LOG_DIR="${APP_BASE}/logs"
CONFIG_DIR="${APP_BASE}/configs"
PID_FILE="${APP_BASE}/${APP_NAME}.pid"
LOG_FILE="${LOG_DIR}/${APP_NAME}.log"
ENV_FILE="${CONFIG_DIR}/app.env"

echo "[INFO] 开始部署 $APP_NAME..."

# 1. 检查JAR文件
if [[ ! -f "target/$JAR_NAME" ]]; then
    echo "[ERROR] JAR文件不存在: target/$JAR_NAME"
    echo "[INFO] 请先运行: mvn clean package -Dmaven.test.skip=true"
    exit 1
fi

# 2. 检查环境配置文件
if [[ ! -f "$ENV_FILE" ]]; then
    echo "[ERROR] 环境配置文件不存在: $ENV_FILE"
    exit 1
fi

# 3. 停止现有应用
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "[INFO] 停止现有应用 (PID: $PID)..."
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
        fi
    fi
    rm -f "$PID_FILE"
fi

# 4. 复制JAR文件到data目录
echo "[INFO] 复制JAR文件到 $JAR_DIR..."
cp "target/$JAR_NAME" "$JAR_DIR/"

# 5. 启动应用
echo "[INFO] 启动应用..."
cd "$JAR_DIR"

# 加载环境变量
source "$ENV_FILE"

# 设置默认JVM参数
if [[ -z "$JAVA_OPTS" ]]; then
    JAVA_OPTS="-Xms512m -Xmx2g -XX:+UseG1GC"
fi

# 启动应用，日志写到logs目录
nohup java $JAVA_OPTS -jar "$JAR_NAME" --spring.profiles.active=prod > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "[INFO] 应用已启动！"
echo "[INFO] PID: $(cat $PID_FILE)"
echo "[INFO] JAR位置: $JAR_DIR/$JAR_NAME"
echo "[INFO] 日志文件: $LOG_FILE"
echo "[INFO] 查看日志: tail -f $LOG_FILE"
echo "[INFO] 停止应用: kill \$(cat $PID_FILE)"

# 检查启动状态
sleep 2
PID=$(cat "$PID_FILE")
if ps -p $PID > /dev/null 2>&1; then
    echo "[SUCCESS] 应用启动成功！"
else
    echo "[ERROR] 应用启动失败，请查看日志: $LOG_FILE"
    exit 1
fi