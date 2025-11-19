from aiohttp import web
from core.api.base_handler import BaseHandler
from config.logger import setup_logging
import mysql.connector
from mysql.connector import Error
import yaml
from pathlib import Path

TAG = __name__


class ChatHistoryHandler(BaseHandler):
    """聊天记录 API 处理器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = setup_logging()
        self.db_config = self._load_db_config()

    def _load_db_config(self):
        """从custom_config.yaml加载数据库配置"""
        try:
            project_dir = Path(__file__).parent.parent.parent
            custom_config_path = project_dir / "custom_config.yaml"
            
            if not custom_config_path.exists():
                self.logger.bind(tag=TAG).warning(f"custom_config.yaml 文件不存在: {custom_config_path}")
                return None
            
            with open(custom_config_path, "r", encoding="utf-8") as f:
                custom_config = yaml.safe_load(f)
            
            # 检查是否启用了read_config_from_api
            read_config_from_api = custom_config.get("read_config_from_api", False)
            
            if not read_config_from_api:
                self.logger.bind(tag=TAG).info("read_config_from_api未启用，聊天记录API将不可用")
                return None
            
            # 从Docker配置或本地配置中读取数据库信息
            mysql_config = custom_config.get("mysql", {})
            
            if not mysql_config:
                self.logger.bind(tag=TAG).warning("未找到MySQL配置")
                return None
            
            db_config = {
                "host": mysql_config.get("host", "localhost"),
                "port": mysql_config.get("port", 3306),
                "user": mysql_config.get("user", "root"),
                "password": mysql_config.get("password", ""),
                "database": mysql_config.get("database", "xiaozhi")
            }
            
            self.logger.bind(tag=TAG).info(f"数据库配置加载成功: {db_config['host']}:{db_config['port']}")
            return db_config
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"加载数据库配置失败: {e}")
            return None

    def _get_db_connection(self):
        """获取数据库连接"""
        if not self.db_config:
            raise Exception("数据库未配置")
        
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            self.logger.bind(tag=TAG).error(f"数据库连接失败: {e}")
            raise

    async def handle_options(self, request):
        """处理 OPTIONS 请求（CORS 预检）"""
        response = web.Response()
        self._add_cors_headers(response)
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    async def handle_get_by_session(self, request):
        """根据session_id获取聊天记录"""
        response = None
        
        try:
            # 获取路径参数
            session_id = request.match_info.get('session_id')
            
            if not session_id:
                response = web.json_response({
                    "success": False,
                    "error": "缺少 session_id 参数"
                })
                self._add_cors_headers(response)
                return response
            
            # 查询数据库
            connection = self._get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id,
                    mac_address,
                    agent_id,
                    session_id,
                    chat_type,
                    content,
                    created_at
                FROM ai_agent_chat_history
                WHERE session_id = %s
                ORDER BY created_at ASC
            """
            
            cursor.execute(query, (session_id,))
            records = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            # 转换为JSON可序列化的格式
            chat_history = []
            for record in records:
                chat_history.append({
                    "id": record["id"],
                    "mac_address": record["mac_address"],
                    "agent_id": record["agent_id"],
                    "session_id": record["session_id"],
                    "chat_type": record["chat_type"],  # 1-用户, 2-智能体
                    "content": record["content"],
                    "created_at": record["created_at"].isoformat() if record["created_at"] else None
                })
            
            response = web.json_response({
                "success": True,
                "data": chat_history,
                "message": f"找到 {len(chat_history)} 条聊天记录"
            })
            self._add_cors_headers(response)
            return response
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"查询聊天记录失败: {e}")
            response = web.json_response({
                "success": False,
                "error": str(e)
            })
            self._add_cors_headers(response)
            return response

    async def handle_check_memory(self, request):
        """检查某会话是否已生成记忆"""
        response = None
        
        try:
            # 获取路径参数
            session_id = request.match_info.get('session_id')
            
            if not session_id:
                response = web.json_response({
                    "success": False,
                    "error": "缺少 session_id 参数"
                })
                self._add_cors_headers(response)
                return response
            
            # 这里需要调用MEMu API检查是否有该session_id的记忆
            # 暂时返回简单响应，实际逻辑需要与MEMu集成
            response = web.json_response({
                "success": True,
                "data": {
                    "session_id": session_id,
                    "has_memory": False,  # 需要实际检查
                    "memory_count": 0
                },
                "message": "检查完成"
            })
            self._add_cors_headers(response)
            return response
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"检查记忆失败: {e}")
            response = web.json_response({
                "success": False,
                "error": str(e)
            })
            self._add_cors_headers(response)
            return response

