from config.logger import setup_logging
from aiohttp import web
import datetime

TAG = __name__
logger = setup_logging()

class LoginHandler:
    def __init__(self, user_manager, session_manager):
        self.user_manager = user_manager
        self.session_manager = session_manager

    async def handle_login(self, request):
        """处理登录请求"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                logger.bind(tag=TAG).warning(f"Login attempt with empty credentials from {request.remote}")
                return web.json_response({
                    'success': False, 
                    'message': '用户名和密码不能为空'
                })

            stored_user = await self.user_manager.get_user(username)
            if not stored_user or stored_user['password'] != self.user_manager.hash_password(password):
                logger.bind(tag=TAG).warning(f"Failed login attempt for user {username} from {request.remote}")
                return web.json_response({
                    'success': False, 
                    'message': '用户名或密码错误'
                })

            # 更新最后登录时间
            await self.user_manager.update_user(username, {
                'last_login': datetime.datetime.now().isoformat()
            })

            # 创建会话并返回session_id
            session_id = self.session_manager.create_session(username)
            return web.json_response({
                'success': True, 
                'message': '登录成功',
                'session_id': session_id
            })

        except Exception as e:
            logger.bind(tag=TAG).error(f"Login error: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False, 
                'message': '登录失败，请稍后重试'
            })
