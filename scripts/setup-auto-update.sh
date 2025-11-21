#!/bin/bash
#============================================
# 小智服务端自动更新功能配置脚本
# 功能：一键安装自动更新脚本和定时任务
#============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置项
INSTALL_DIR="/opt/xiaozhi-server"
SCRIPT_URL="https://raw.githubusercontent.com/BladeRunner18/xiaozhi-esp32-server/main/auto-update.sh"

# 打印带颜色的消息
print_message() {
    local level=$1
    shift
    local message="$@"
    
    case $level in
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# 显示标题
show_banner() {
    echo ""
    echo -e "${GREEN}=========================================="
    echo "  小智服务端自动更新功能配置"
    echo "==========================================${NC}"
    echo ""
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_message ERROR "请使用 root 权限运行此脚本"
        echo "使用方法: sudo $0"
        exit 1
    fi
}

# 检查项目目录
check_project_dir() {
    print_message INFO "检查项目目录..."
    
    if [ ! -d "$INSTALL_DIR" ]; then
        print_message ERROR "项目目录不存在: $INSTALL_DIR"
        print_message INFO "请先运行 docker-setup.sh 完成初始安装"
        exit 1
    fi
    
    if [ ! -f "$INSTALL_DIR/docker-compose_all.yml" ]; then
        print_message ERROR "docker-compose 配置文件不存在"
        exit 1
    fi
    
    print_message SUCCESS "项目目录检查通过"
}

# 创建必要的目录
create_directories() {
    print_message INFO "创建必要的目录..."
    
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/backup"
    
    print_message SUCCESS "目录创建完成"
}

# 安装自动更新脚本
install_update_script() {
    print_message INFO "安装自动更新脚本..."
    
    local script_path="$INSTALL_DIR/auto-update.sh"
    
    # 从 GitHub 下载（如果可用）
    if curl --version &>/dev/null; then
        print_message INFO "从 GitHub 下载最新版本..."
        if curl -fsSL "$SCRIPT_URL" -o "$script_path" 2>/dev/null; then
            print_message SUCCESS "已下载最新版本"
        else
            print_message WARNING "无法从 GitHub 下载，使用本地文件"
            # 如果下载失败，复制仓库中的文件
            if [ -f "./auto-update.sh" ]; then
                cp "./auto-update.sh" "$script_path"
            else
                print_message ERROR "找不到 auto-update.sh 文件"
                exit 1
            fi
        fi
    else
        # 没有 curl，使用本地文件
        if [ -f "./auto-update.sh" ]; then
            cp "./auto-update.sh" "$script_path"
        else
            print_message ERROR "找不到 auto-update.sh 文件"
            exit 1
        fi
    fi
    
    # 赋予执行权限
    chmod +x "$script_path"
    
    print_message SUCCESS "自动更新脚本安装完成: $script_path"
}

# 配置定时任务
setup_crontab() {
    print_message INFO "配置定时任务..."
    
    # 提示用户选择更新频率
    echo ""
    echo "请选择自动更新频率："
    echo "1) 每天凌晨 2 点 (推荐)"
    echo "2) 每天凌晨 3 点"
    echo "3) 每 6 小时一次"
    echo "4) 每小时一次"
    echo "5) 每周日凌晨 2 点"
    echo "6) 自定义"
    echo "7) 跳过 (手动更新)"
    echo ""
    
    read -p "请输入选项 [1-7]: " choice
    
    case $choice in
        1)
            CRON_SCHEDULE="0 2 * * *"
            CRON_DESC="每天凌晨 2 点"
            ;;
        2)
            CRON_SCHEDULE="0 3 * * *"
            CRON_DESC="每天凌晨 3 点"
            ;;
        3)
            CRON_SCHEDULE="0 */6 * * *"
            CRON_DESC="每 6 小时一次"
            ;;
        4)
            CRON_SCHEDULE="0 * * * *"
            CRON_DESC="每小时一次"
            ;;
        5)
            CRON_SCHEDULE="0 2 * * 0"
            CRON_DESC="每周日凌晨 2 点"
            ;;
        6)
            read -p "请输入 cron 表达式 (如 '0 2 * * *'): " CRON_SCHEDULE
            CRON_DESC="自定义: $CRON_SCHEDULE"
            ;;
        7)
            print_message INFO "跳过定时任务配置"
            return 0
            ;;
        *)
            print_message WARNING "无效选项，使用默认值: 每天凌晨 2 点"
            CRON_SCHEDULE="0 2 * * *"
            CRON_DESC="每天凌晨 2 点"
            ;;
    esac
    
    # 添加到 crontab
    CRON_JOB="$CRON_SCHEDULE $INSTALL_DIR/auto-update.sh >> $INSTALL_DIR/logs/auto-update.log 2>&1"
    
    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "auto-update.sh"; then
        print_message WARNING "定时任务已存在"
        read -p "是否替换现有定时任务? [y/N]: " replace
        
        if [[ $replace =~ ^[Yy]$ ]]; then
            # 删除旧的
            crontab -l 2>/dev/null | grep -v "auto-update.sh" | crontab -
            # 添加新的
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            print_message SUCCESS "定时任务已更新: $CRON_DESC"
        else
            print_message INFO "保留现有定时任务"
        fi
    else
        # 添加新的
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        print_message SUCCESS "定时任务已添加: $CRON_DESC"
    fi
}

# 测试运行
test_run() {
    echo ""
    read -p "是否立即执行一次更新测试? [Y/n]: " test
    
    if [[ ! $test =~ ^[Nn]$ ]]; then
        print_message INFO "开始测试运行..."
        echo ""
        
        if "$INSTALL_DIR/auto-update.sh"; then
            print_message SUCCESS "测试运行成功！"
        else
            print_message WARNING "测试运行完成，请检查日志"
        fi
    fi
}

# 显示使用说明
show_usage() {
    echo ""
    print_message INFO "=========================================="
    print_message SUCCESS "配置完成！"
    print_message INFO "=========================================="
    echo ""
    echo "📁 安装位置:"
    echo "   脚本: $INSTALL_DIR/auto-update.sh"
    echo "   日志: $INSTALL_DIR/logs/auto-update.log"
    echo "   备份: $INSTALL_DIR/backup/"
    echo ""
    echo "📝 常用命令:"
    echo "   手动更新:     $INSTALL_DIR/auto-update.sh"
    echo "   查看日志:     tail -f $INSTALL_DIR/logs/auto-update.log"
    echo "   查看定时任务: crontab -l"
    echo "   编辑定时任务: crontab -e"
    echo "   服务管理:     $INSTALL_DIR/manage.sh"
    echo ""
    echo "📊 定时任务信息:"
    crontab -l 2>/dev/null | grep "auto-update.sh" || echo "   未配置定时任务"
    echo ""
    print_message INFO "=========================================="
    echo ""
}

# 主函数
main() {
    show_banner
    
    check_root
    check_project_dir
    create_directories
    install_update_script
    setup_crontab
    test_run
    show_usage
    
    print_message SUCCESS "全部完成！小智服务端将自动保持最新版本 🎉"
    echo ""
}

# 捕获中断信号
trap 'echo ""; print_message WARNING "安装已取消"; exit 1' INT TERM

# 执行主函数
main "$@"

