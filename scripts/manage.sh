#!/bin/bash

case "$1" in
    update)
        echo "🔄 执行更新..."
        /opt/xiaozhi-server/auto-update.sh
        ;;
    
    status)
        echo "📊 服务状态："
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml ps
        ;;
    
    logs)
        SERVICE=${2:-xiaozhi-esp32-server}
        echo "📄 查看 $SERVICE 日志："
        docker logs -f --tail=100 "$SERVICE"
        ;;
    
    restart)
        echo "♻️  重启服务..."
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml restart
        ;;
    
    *)
        echo "用法: $0 {update|status|logs|restart}"
        echo ""
        echo "命令说明："
        echo "  update   - 检查并更新到最新版本"
        echo "  status   - 查看服务运行状态"
        echo "  logs     - 查看服务日志 (可选参数: 服务名)"
        echo "  restart  - 重启所有服务"
        exit 1
        ;;
esac