#!/bin/bash

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/main/xiaozhi-server/test"

# 设置端口号
PORT=8020

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 清理函数：确保服务器进程被正确关闭
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务器...${NC}"
    if [ ! -z "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
    fi
    # 额外检查：关闭可能遗留的进程
    lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✓ 服务器已停止${NC}"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM EXIT

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  XiaoZhi ESP32 Test Server${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查目录是否存在
if [ ! -d "$TEST_DIR" ]; then
    echo "错误：test 目录不存在: $TEST_DIR"
    exit 1
fi

# 检查 test_page.html 是否存在
if [ ! -f "$TEST_DIR/test_page.html" ]; then
    echo "错误：test_page.html 文件不存在"
    exit 1
fi

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ 端口 $PORT 已被占用，正在尝试关闭占用进程...${NC}"
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# 进入 test 目录
cd "$TEST_DIR" || exit 1

echo -e "${GREEN}✓ 进入目录: $TEST_DIR${NC}"
echo -e "${GREEN}✓ 启动 HTTP 服务器在端口 $PORT${NC}"
echo ""
echo -e "${BLUE}访问地址: http://localhost:$PORT/test_page.html${NC}"
echo -e "${BLUE}按 Ctrl+C 停止服务器${NC}"
echo ""

# 在后台启动 Python HTTP 服务器
python3 -m http.server $PORT &
SERVER_PID=$!

# 等待服务器启动
sleep 2

# 检查服务器是否成功启动
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${YELLOW}错误：服务器启动失败${NC}"
    exit 1
fi

# 在浏览器中打开
if command -v open &> /dev/null; then
    # macOS
    open "http://localhost:$PORT/test_page.html"
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open "http://localhost:$PORT/test_page.html"
elif command -v start &> /dev/null; then
    # Windows (Git Bash)
    start "http://localhost:$PORT/test_page.html"
else
    echo "请手动在浏览器中打开: http://localhost:$PORT/test_page.html"
fi

# 等待服务器进程（这里会响应 Ctrl+C）
wait $SERVER_PID
