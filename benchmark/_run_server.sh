#!/bin/bash
# 在 main/xiaozhi-server 目录启服务（端口 18000）。
# 通过 SERVER_DIR / PORT / PID_FILE / LOG_FILE 环境变量覆盖默认值。
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="${SERVER_DIR:-$REPO_ROOT/main/xiaozhi-server}"
PORT="${PORT:-18000}"
PID_FILE="${PID_FILE:-$SERVER_DIR/.run/server.pid}"
LOG_FILE="${LOG_FILE:-$SERVER_DIR/.run/server.log}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [ -f "$PID_FILE" ]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

cd "$SERVER_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
nohup "$PYTHON_BIN" app.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "started pid=$SERVER_PID port=$PORT log=$LOG_FILE"
disown
