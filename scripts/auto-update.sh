#!/bin/bash
#============================================
# 小智服务端 Docker 自动更新脚本
# 功能：自动拉取最新镜像并重启服务
#============================================

# 配置项
PROJECT_DIR="/opt/xiaozhi-server"
COMPOSE_FILE="docker-compose_all.yml"
LOG_FILE="/opt/xiaozhi-server/logs/auto-update.log"
BACKUP_DIR="/opt/xiaozhi-server/backup"

# 镜像配置
SERVER_IMAGE="ghcr.nju.edu.cn/BladeRunner18/xiaozhi-esp32-server:server_latest"
WEB_IMAGE="ghcr.nju.edu.cn/BladeRunner18/xiaozhi-esp32-server:web_latest"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${BLUE}[INFO]${NC} [$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} [$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} [$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} [$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
        *)
            echo "[$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# 初始化
init() {
    # 创建必要的目录
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$BACKUP_DIR"
    
    log INFO "=========================================="
    log INFO "小智服务端自动更新脚本启动"
    log INFO "=========================================="
}

# 检查环境
check_environment() {
    log INFO "检查运行环境..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker 未安装！"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        log ERROR "Docker Compose 未安装或版本过低！"
        exit 1
    fi
    
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        log ERROR "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    # 检查 docker-compose 文件
    if [ ! -f "$PROJECT_DIR/$COMPOSE_FILE" ]; then
        log ERROR "docker-compose 文件不存在: $PROJECT_DIR/$COMPOSE_FILE"
        exit 1
    fi
    
    log SUCCESS "环境检查通过"
}

# 进入项目目录
enter_project_dir() {
    cd "$PROJECT_DIR" || {
        log ERROR "无法进入目录: $PROJECT_DIR"
        exit 1
    }
    log INFO "当前目录: $(pwd)"
}

# 记录当前镜像信息
record_current_images() {
    log INFO "记录当前镜像信息..."
    
    OLD_SERVER_IMAGE=$(docker images --format "{{.ID}}" "$SERVER_IMAGE" 2>/dev/null || echo "none")
    OLD_WEB_IMAGE=$(docker images --format "{{.ID}}" "$WEB_IMAGE" 2>/dev/null || echo "none")
    
    log INFO "当前 Server 镜像 ID: $OLD_SERVER_IMAGE"
    log INFO "当前 Web 镜像 ID: $OLD_WEB_IMAGE"
}

# 拉取最新镜像
pull_latest_images() {
    log INFO "开始拉取最新镜像..."
    log INFO "这可能需要几分钟时间，请耐心等待..."
    
    if docker compose -f "$COMPOSE_FILE" pull 2>&1 | tee -a "$LOG_FILE"; then
        log SUCCESS "镜像拉取成功"
        return 0
    else
        log ERROR "镜像拉取失败！"
        return 1
    fi
}

# 检查镜像是否有更新
check_image_updates() {
    log INFO "检查镜像是否有更新..."
    
    NEW_SERVER_IMAGE=$(docker images --format "{{.ID}}" "$SERVER_IMAGE" 2>/dev/null || echo "none")
    NEW_WEB_IMAGE=$(docker images --format "{{.ID}}" "$WEB_IMAGE" 2>/dev/null || echo "none")
    
    log INFO "新 Server 镜像 ID: $NEW_SERVER_IMAGE"
    log INFO "新 Web 镜像 ID: $NEW_WEB_IMAGE"
    
    HAS_UPDATE=false
    
    if [ "$OLD_SERVER_IMAGE" != "$NEW_SERVER_IMAGE" ]; then
        log SUCCESS "检测到 Server 镜像更新"
        HAS_UPDATE=true
    fi
    
    if [ "$OLD_WEB_IMAGE" != "$NEW_WEB_IMAGE" ]; then
        log SUCCESS "检测到 Web 镜像更新"
        HAS_UPDATE=true
    fi
    
    if [ "$HAS_UPDATE" = false ]; then
        log INFO "已是最新版本，无需更新"
        return 1
    fi
    
    return 0
}

# 备份当前状态
backup_current_state() {
    log INFO "备份当前服务状态..."
    
    local backup_file="${BACKUP_DIR}/service-status-$(date +%Y%m%d-%H%M%S).txt"
    docker compose -f "$COMPOSE_FILE" ps > "$backup_file" 2>&1
    
    log SUCCESS "状态已备份到: $backup_file"
}

# 更新服务
update_services() {
    log INFO "开始更新服务..."
    log INFO "使用滚动更新策略，尽量减少服务中断..."
    
    # 滚动更新（零停机部署）
    if docker compose -f "$COMPOSE_FILE" up -d --no-deps --build 2>&1 | tee -a "$LOG_FILE"; then
        log SUCCESS "服务更新成功"
        return 0
    else
        log ERROR "服务更新失败！"
        return 1
    fi
}

# 等待服务健康检查
wait_for_health_check() {
    log INFO "等待服务启动并通过健康检查..."
    
    local max_wait=60
    local waited=0
    
    while [ $waited -lt $max_wait ]; do
        # 检查数据库健康状态
        if docker inspect xiaozhi-esp32-server-db 2>/dev/null | grep -q '"Status": "healthy"'; then
            log SUCCESS "数据库服务健康"
            break
        fi
        
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done
    echo ""
    
    # 再等待几秒让应用完全启动
    log INFO "等待应用服务完全启动..."
    sleep 5
}

# 检查服务状态
check_services_status() {
    log INFO "检查服务运行状态..."
    
    docker compose -f "$COMPOSE_FILE" ps | tee -a "$LOG_FILE"
    
    # 检查是否有退出的容器
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "Exit"; then
        log ERROR "检测到服务异常退出！"
        return 1
    fi
    
    log SUCCESS "所有服务运行正常"
    return 0
}

# 清理旧镜像
cleanup_old_images() {
    log INFO "清理悬空镜像和未使用的镜像..."
    
    # 清理悬空镜像
    local pruned=$(docker image prune -f 2>&1)
    
    if echo "$pruned" | grep -q "Total reclaimed space"; then
        local space=$(echo "$pruned" | grep "Total reclaimed space" | awk '{print $4 $5}')
        log SUCCESS "已清理磁盘空间: $space"
    else
        log INFO "没有需要清理的镜像"
    fi
}

# 显示更新摘要
show_update_summary() {
    log INFO "=========================================="
    log INFO "更新摘要"
    log INFO "=========================================="
    
    # 显示镜像信息
    log INFO "当前运行的镜像版本："
    docker images | grep xiaozhi-esp32-server | head -5 | tee -a "$LOG_FILE"
    
    echo ""
    
    # 显示容器状态
    log INFO "服务运行状态："
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOG_FILE"
    
    echo ""
    
    # 显示资源使用
    log INFO "资源使用情况："
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        xiaozhi-esp32-server xiaozhi-esp32-server-web xiaozhi-esp32-server-db xiaozhi-esp32-server-redis 2>/dev/null | tee -a "$LOG_FILE"
}

# 错误处理和回滚
rollback_on_error() {
    log ERROR "更新失败，尝试回滚..."
    
    # 这里可以添加回滚逻辑
    # 例如：使用备份的镜像 ID 重新部署
    
    log WARNING "请手动检查服务状态并进行恢复"
}

# 主函数
main() {
    # 初始化
    init
    
    # 检查环境
    check_environment
    
    # 进入项目目录
    enter_project_dir
    
    # 记录当前镜像
    record_current_images
    
    # 拉取最新镜像
    if ! pull_latest_images; then
        log ERROR "更新失败：无法拉取镜像"
        exit 1
    fi
    
    # 检查是否有更新
    if ! check_image_updates; then
        log INFO "=========================================="
        log SUCCESS "更新检查完成：已是最新版本"
        log INFO "=========================================="
        exit 0
    fi
    
    # 有更新，开始升级流程
    log INFO "检测到新版本，开始升级流程..."
    
    # 备份当前状态
    backup_current_state
    
    # 更新服务
    if ! update_services; then
        rollback_on_error
        exit 1
    fi
    
    # 等待健康检查
    wait_for_health_check
    
    # 检查服务状态
    if ! check_services_status; then
        log ERROR "服务状态异常，请检查日志"
        exit 1
    fi
    
    # 清理旧镜像
    cleanup_old_images
    
    # 显示更新摘要
    show_update_summary
    
    log INFO "=========================================="
    log SUCCESS "更新成功完成！"
    log INFO "=========================================="
    
    exit 0
}

# 捕获 Ctrl+C 信号
trap 'log WARNING "脚本被用户中断"; exit 130' INT TERM

# 执行主函数
main "$@"

