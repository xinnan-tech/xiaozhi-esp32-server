#!/bin/bash
#============================================
# 小智服务端 Docker 自动更新脚本
# 功能：自动拉取最新镜像并零停机重启服务
# 版本：2.0（生产级）
#============================================

set -euo pipefail  # 严格模式：遇到错误立即退出

# ==================== 配置项 ====================
PROJECT_DIR="/opt/xiaozhi-server"
COMPOSE_FILE="docker-compose_all.yml"
LOG_FILE="/opt/xiaozhi-server/logs/auto-update.log"
BACKUP_DIR="/opt/xiaozhi-server/backup"
LOCK_FILE="/tmp/xiaozhi-auto-update.lock"

# 镜像配置（已修正为正确的地址，使用国内镜像加速）
SERVER_IMAGE="ghcr.nju.edu.cn/bladerunner18/xiaozhi-esp32-server:server_latest"
WEB_IMAGE="ghcr.nju.edu.cn/bladerunner18/xiaozhi-esp32-server:web_latest"

# 健康检查配置
HEALTH_CHECK_TIMEOUT=120  # 健康检查超时时间（秒）
HEALTH_CHECK_INTERVAL=5   # 健康检查间隔（秒）

# 磁盘空间要求（MB）
MIN_FREE_SPACE=2048  # 至少需要 2GB 空闲空间

# 日志配置
MAX_LOG_SIZE=10485760  # 10MB
MAX_LOG_FILES=5

# 服务名称列表
SERVICES=("xiaozhi-esp32-server" "xiaozhi-esp32-server-web" "xiaozhi-esp32-server-db" "xiaozhi-esp32-server-redis")

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ==================== 日志函数 ====================
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
        DEBUG)
            echo -e "${PURPLE}[DEBUG]${NC} [$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
        *)
            echo "[$timestamp] $message" | tee -a "$LOG_FILE"
            ;;
    esac
}

# ==================== 日志轮转 ====================
rotate_logs() {
    if [ -f "$LOG_FILE" ]; then
        local log_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
        
        if [ "$log_size" -gt "$MAX_LOG_SIZE" ]; then
            log INFO "日志文件超过限制，执行轮转..."
            
            # 删除最旧的日志
            [ -f "${LOG_FILE}.${MAX_LOG_FILES}" ] && rm -f "${LOG_FILE}.${MAX_LOG_FILES}"
            
            # 轮转日志文件
            for i in $(seq $((MAX_LOG_FILES-1)) -1 1); do
                [ -f "${LOG_FILE}.${i}" ] && mv "${LOG_FILE}.${i}" "${LOG_FILE}.$((i+1))"
            done
            
            # 归档当前日志
            mv "$LOG_FILE" "${LOG_FILE}.1"
            touch "$LOG_FILE"
        fi
    fi
}

# ==================== 锁机制 ====================
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log ERROR "另一个更新进程正在运行 (PID: $pid)"
            exit 1
        else
            log WARNING "发现过期的锁文件，已清理"
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
    log DEBUG "已获取更新锁 (PID: $$)"
}

release_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log DEBUG "已释放更新锁"
    fi
}

# ==================== 初始化 ====================
init() {
    # 创建必要的目录
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$BACKUP_DIR"
    
    # 日志轮转
    rotate_logs
    
    log INFO "=========================================="
    log INFO "小智服务端自动更新脚本启动 v2.0"
    log INFO "=========================================="
    
    # 获取锁
    acquire_lock
}

# ==================== 环境检查 ====================
check_environment() {
    log INFO "检查运行环境..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker 未安装！"
        exit 1
    fi
    
    local docker_version=$(docker --version)
    log INFO "Docker 版本: $docker_version"
    
    # 检查 Docker Compose
    if ! docker compose version &> /dev/null; then
        log ERROR "Docker Compose 未安装或版本过低！需要 Compose V2"
        exit 1
    fi
    
    local compose_version=$(docker compose version)
    log INFO "Docker Compose 版本: $compose_version"
    
    # 检查 Docker 守护进程
    if ! docker info &> /dev/null; then
        log ERROR "Docker 守护进程未运行！"
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

# ==================== 磁盘空间检查 ====================
check_disk_space() {
    log INFO "检查磁盘空间..."
    
    # 获取可用空间（KB）
    local available_space=$(df -k "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    local available_mb=$((available_space / 1024))
    
    log INFO "可用磁盘空间: ${available_mb}MB"
    
    if [ "$available_mb" -lt "$MIN_FREE_SPACE" ]; then
        log ERROR "磁盘空间不足！需要至少 ${MIN_FREE_SPACE}MB，当前仅有 ${available_mb}MB"
        exit 1
    fi
    
    log SUCCESS "磁盘空间充足"
}

# ==================== 进入项目目录 ====================
enter_project_dir() {
    cd "$PROJECT_DIR" || {
        log ERROR "无法进入目录: $PROJECT_DIR"
        exit 1
    }
    log INFO "工作目录: $(pwd)"
}

# ==================== 记录当前镜像信息 ====================
record_current_images() {
    log INFO "记录当前镜像信息..."
    
    # 记录镜像 ID
    OLD_SERVER_IMAGE=$(docker images --format "{{.ID}}" "$SERVER_IMAGE" 2>/dev/null | head -1 || echo "none")
    OLD_WEB_IMAGE=$(docker images --format "{{.ID}}" "$WEB_IMAGE" 2>/dev/null | head -1 || echo "none")
    
    # 记录镜像 Digest（用于完整性验证）
    OLD_SERVER_DIGEST=$(docker images --digests --format "{{.Digest}}" "$SERVER_IMAGE" 2>/dev/null | head -1 || echo "none")
    OLD_WEB_DIGEST=$(docker images --digests --format "{{.Digest}}" "$WEB_IMAGE" 2>/dev/null | head -1 || echo "none")
    
    log INFO "当前 Server 镜像 ID: $OLD_SERVER_IMAGE"
    log INFO "当前 Web 镜像 ID: $OLD_WEB_IMAGE"
    log DEBUG "Server Digest: $OLD_SERVER_DIGEST"
    log DEBUG "Web Digest: $OLD_WEB_DIGEST"
    
    # 导出镜像 ID 供回滚使用
    export OLD_SERVER_IMAGE OLD_WEB_IMAGE
}

# ==================== 拉取最新镜像 ====================
pull_latest_images() {
    log INFO "开始拉取最新镜像..."
    log INFO "这可能需要几分钟时间，请耐心等待..."
    
    # 设置拉取超时
    if timeout 600 docker compose -f "$COMPOSE_FILE" pull --quiet 2>&1 | tee -a "$LOG_FILE"; then
        log SUCCESS "镜像拉取成功"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log ERROR "镜像拉取超时（10分钟）"
        else
            log ERROR "镜像拉取失败，退出码: $exit_code"
        fi
        return 1
    fi
}

# ==================== 检查镜像是否有更新 ====================
check_image_updates() {
    log INFO "检查镜像是否有更新..."
    
    NEW_SERVER_IMAGE=$(docker images --format "{{.ID}}" "$SERVER_IMAGE" 2>/dev/null | head -1 || echo "none")
    NEW_WEB_IMAGE=$(docker images --format "{{.ID}}" "$WEB_IMAGE" 2>/dev/null | head -1 || echo "none")
    
    NEW_SERVER_DIGEST=$(docker images --digests --format "{{.Digest}}" "$SERVER_IMAGE" 2>/dev/null | head -1 || echo "none")
    NEW_WEB_DIGEST=$(docker images --digests --format "{{.Digest}}" "$WEB_IMAGE" 2>/dev/null | head -1 || echo "none")
    
    log INFO "新 Server 镜像 ID: $NEW_SERVER_IMAGE"
    log INFO "新 Web 镜像 ID: $NEW_WEB_IMAGE"
    log DEBUG "新 Server Digest: $NEW_SERVER_DIGEST"
    log DEBUG "新 Web Digest: $NEW_WEB_DIGEST"
    
    HAS_UPDATE=false
    
    if [ "$OLD_SERVER_IMAGE" != "$NEW_SERVER_IMAGE" ] && [ "$NEW_SERVER_IMAGE" != "none" ]; then
        log SUCCESS "检测到 Server 镜像更新 ($OLD_SERVER_IMAGE -> $NEW_SERVER_IMAGE)"
        HAS_UPDATE=true
    fi
    
    if [ "$OLD_WEB_IMAGE" != "$NEW_WEB_IMAGE" ] && [ "$NEW_WEB_IMAGE" != "none" ]; then
        log SUCCESS "检测到 Web 镜像更新 ($OLD_WEB_IMAGE -> $NEW_WEB_IMAGE)"
        HAS_UPDATE=true
    fi
    
    if [ "$HAS_UPDATE" = false ]; then
        log INFO "已是最新版本，无需更新"
        return 1
    fi
    
    return 0
}

# ==================== 备份当前状态 ====================
backup_current_state() {
    log INFO "备份当前服务状态..."
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${BACKUP_DIR}/backup-${timestamp}.tar.gz"
    local temp_dir="${BACKUP_DIR}/temp-${timestamp}"
    
    mkdir -p "$temp_dir"
    
    # 备份服务状态
    docker compose -f "$COMPOSE_FILE" ps --format json > "${temp_dir}/service-status.json" 2>&1 || true
    
    # 备份容器信息
    for service in "${SERVICES[@]}"; do
        if docker inspect "$service" &> /dev/null; then
            docker inspect "$service" > "${temp_dir}/${service}-inspect.json" 2>&1 || true
        fi
    done
    
    # 备份镜像信息
    echo "OLD_SERVER_IMAGE=$OLD_SERVER_IMAGE" > "${temp_dir}/image-info.env"
    echo "OLD_WEB_IMAGE=$OLD_WEB_IMAGE" >> "${temp_dir}/image-info.env"
    echo "OLD_SERVER_DIGEST=$OLD_SERVER_DIGEST" >> "${temp_dir}/image-info.env"
    echo "OLD_WEB_DIGEST=$OLD_WEB_DIGEST" >> "${temp_dir}/image-info.env"
    
    # 备份 docker-compose 文件
    cp "$PROJECT_DIR/$COMPOSE_FILE" "${temp_dir}/" 2>&1 || true
    
    # 打包备份
    tar -czf "$backup_file" -C "$temp_dir" . 2>&1 || true
    rm -rf "$temp_dir"
    
    # 清理旧备份（保留最近10个）
    ls -t "${BACKUP_DIR}"/backup-*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
    
    export BACKUP_FILE="$backup_file"
    log SUCCESS "状态已备份到: $backup_file"
}

# ==================== 更新服务（零停机） ====================
update_services() {
    log INFO "开始零停机更新服务..."
    
    # 使用 up -d 进行滚动更新
    # --remove-orphans: 清理孤立容器
    # --wait: 等待服务健康
    if docker compose -f "$COMPOSE_FILE" up -d --remove-orphans --wait --wait-timeout "$HEALTH_CHECK_TIMEOUT" 2>&1 | tee -a "$LOG_FILE"; then
        log SUCCESS "服务更新命令执行成功"
        return 0
    else
        log ERROR "服务更新失败！"
        return 1
    fi
}

# ==================== 完善的健康检查 ====================
wait_for_health_check() {
    log INFO "执行全面健康检查..."
    
    local max_wait=$HEALTH_CHECK_TIMEOUT
    local waited=0
    local all_healthy=false
    
    while [ $waited -lt $max_wait ]; do
        all_healthy=true
        local status_report=""
        
        # 检查每个服务
        for service in "${SERVICES[@]}"; do
            if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
                # 容器运行中
                
                # 检查健康状态（如果定义了 healthcheck）
                local health_status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$service" 2>/dev/null || echo "unknown")
                
                if [ "$health_status" = "healthy" ] || [ "$health_status" = "no-healthcheck" ]; then
                    status_report="${status_report}✓ $service: healthy\n"
                else
                    status_report="${status_report}✗ $service: $health_status\n"
                    all_healthy=false
                fi
            else
                status_report="${status_report}✗ $service: not running\n"
                all_healthy=false
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            echo ""
            log SUCCESS "所有服务健康检查通过"
            echo -e "$status_report"
            return 0
        fi
        
        # 等待并重试
        sleep "$HEALTH_CHECK_INTERVAL"
        waited=$((waited + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    echo ""
    log ERROR "健康检查超时！当前状态："
    echo -e "$status_report"
    return 1
}

# ==================== 检查服务状态 ====================
check_services_status() {
    log INFO "检查服务运行状态..."
    
    docker compose -f "$COMPOSE_FILE" ps | tee -a "$LOG_FILE"
    
    # 检查是否有退出或不健康的容器
    local unhealthy_count=0
    
    for service in "${SERVICES[@]}"; do
        if ! docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            log ERROR "服务 $service 未运行！"
            ((unhealthy_count++))
        fi
    done
    
    if [ $unhealthy_count -gt 0 ]; then
        log ERROR "检测到 $unhealthy_count 个服务异常！"
        return 1
    fi
    
    log SUCCESS "所有服务运行正常"
    return 0
}

# ==================== 回滚机制 ====================
rollback_on_error() {
    log ERROR "=========================================="
    log ERROR "更新失败，开始自动回滚..."
    log ERROR "=========================================="
    
    if [ -z "${BACKUP_FILE:-}" ] || [ ! -f "$BACKUP_FILE" ]; then
        log ERROR "未找到备份文件，无法自动回滚"
        log WARNING "请手动检查服务状态并进行恢复"
        return 1
    fi
    
    log INFO "使用备份文件: $BACKUP_FILE"
    
    # 提取备份信息
    local temp_restore="${BACKUP_DIR}/restore-temp"
    mkdir -p "$temp_restore"
    tar -xzf "$BACKUP_FILE" -C "$temp_restore" 2>&1 || {
        log ERROR "解压备份文件失败"
        rm -rf "$temp_restore"
        return 1
    }
    
    # 读取旧镜像 ID
    if [ -f "${temp_restore}/image-info.env" ]; then
        source "${temp_restore}/image-info.env"
        
        log INFO "准备回滚到旧版本："
        log INFO "  Server 镜像: $OLD_SERVER_IMAGE"
        log INFO "  Web 镜像: $OLD_WEB_IMAGE"
        
        # 检查旧镜像是否还存在
        if docker image inspect "$OLD_SERVER_IMAGE" &> /dev/null && \
           docker image inspect "$OLD_WEB_IMAGE" &> /dev/null; then
            
            log INFO "旧镜像仍然存在，执行回滚..."
            
            # 标记旧镜像为最新（临时）
            docker tag "$OLD_SERVER_IMAGE" "$SERVER_IMAGE" 2>&1 | tee -a "$LOG_FILE" || true
            docker tag "$OLD_WEB_IMAGE" "$WEB_IMAGE" 2>&1 | tee -a "$LOG_FILE" || true
            
            # 重启服务
            log INFO "使用旧镜像重启服务..."
            docker compose -f "$COMPOSE_FILE" up -d --force-recreate 2>&1 | tee -a "$LOG_FILE"
            
            # 等待服务恢复
            sleep 10
            
            if check_services_status; then
                log SUCCESS "回滚成功！服务已恢复到之前的版本"
                rm -rf "$temp_restore"
                return 0
            else
                log ERROR "回滚后服务仍然异常"
            fi
        else
            log ERROR "旧镜像已被删除，无法回滚"
        fi
    else
        log ERROR "备份中未找到镜像信息"
    fi
    
    rm -rf "$temp_restore"
    log ERROR "自动回滚失败，请手动恢复"
    log WARNING "您可以使用以下命令手动查看日志："
    log WARNING "  docker compose -f $PROJECT_DIR/$COMPOSE_FILE logs --tail=100"
    
    return 1
}

# ==================== 清理旧镜像 ====================
cleanup_old_images() {
    log INFO "清理悬空镜像和未使用的镜像..."
    
    # 只清理悬空镜像（dangling），保留旧版本镜像以便回滚
    local pruned=$(docker image prune -f 2>&1)
    
    if echo "$pruned" | grep -q "Total reclaimed space"; then
        local space=$(echo "$pruned" | grep "Total reclaimed space" | awk '{print $4 $5}')
        log SUCCESS "已清理磁盘空间: $space"
    else
        log INFO "没有需要清理的悬空镜像"
    fi
    
    # 显示当前镜像占用
    log INFO "当前 Docker 镜像占用："
    docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" | grep -E "^(TYPE|Images)" | tee -a "$LOG_FILE"
}

# ==================== 显示更新摘要 ====================
show_update_summary() {
    log INFO "=========================================="
    log INFO "更新摘要"
    log INFO "=========================================="
    
    # 显示镜像信息
    log INFO "当前运行的镜像版本："
    docker images | grep -E "(REPOSITORY|xiaozhi-esp32-server)" | head -6 | tee -a "$LOG_FILE"
    
    echo ""
    
    # 显示容器状态
    log INFO "服务运行状态："
    docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOG_FILE"
    
    echo ""
    
    # 显示资源使用
    log INFO "资源使用情况："
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(echo "${SERVICES[@]}") 2>/dev/null | tee -a "$LOG_FILE" || log WARNING "无法获取资源使用统计"
    
    echo ""
    
    # 显示备份信息
    if [ -n "${BACKUP_FILE:-}" ]; then
        log INFO "本次更新备份文件: $BACKUP_FILE"
    fi
}

# ==================== 清理函数 ====================
cleanup() {
    log DEBUG "执行清理..."
    release_lock
}

# ==================== 主函数 ====================
main() {
    # 初始化
    init
    
    # 检查环境
    check_environment
    
    # 检查磁盘空间
    check_disk_space
    
    # 进入项目目录
    enter_project_dir
    
    # 记录当前镜像
    record_current_images
    
    # 拉取最新镜像
    if ! pull_latest_images; then
        log ERROR "更新失败：无法拉取镜像"
        cleanup
        exit 1
    fi
    
    # 检查是否有更新
    if ! check_image_updates; then
        log INFO "=========================================="
        log SUCCESS "更新检查完成：已是最新版本"
        log INFO "=========================================="
        cleanup
        exit 0
    fi
    
    # 有更新，开始升级流程
    log INFO "检测到新版本，开始升级流程..."
    
    # 备份当前状态
    backup_current_state
    
    # 更新服务
    if ! update_services; then
        rollback_on_error
        cleanup
        exit 1
    fi
    
    # 完善的健康检查
    if ! wait_for_health_check; then
        log ERROR "健康检查失败！"
        rollback_on_error
        cleanup
        exit 1
    fi
    
    # 最终状态检查
    if ! check_services_status; then
        log ERROR "服务状态异常！"
        rollback_on_error
        cleanup
        exit 1
    fi
    
    # 清理旧镜像
    cleanup_old_images
    
    # 显示更新摘要
    show_update_summary
    
    log INFO "=========================================="
    log SUCCESS "✨ 更新成功完成！"
    log INFO "=========================================="
    
    cleanup
    exit 0
}

# ==================== 信号处理 ====================
trap 'log WARNING "脚本被用户中断"; cleanup; exit 130' INT TERM
trap 'cleanup' EXIT

# ==================== 执行主函数 ====================
main "$@"
