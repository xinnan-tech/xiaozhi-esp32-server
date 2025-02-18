from config.logger import setup_logging
from aiohttp import web
import datetime

TAG = __name__
logger = setup_logging()

class RegisterHandler:
    def __init__(self, user_manager):
        self.user_manager = user_manager

    async def handle_register(self, request):
        """处理注册请求"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                logger.bind(tag=TAG).warning(f"Registration attempt with empty credentials from {request.remote}")
                return web.json_response({
                    'success': False,
                    'message': '用户名和密码不能为空'
                })

            # 检查用户是否已存在
            if await self.user_manager.get_user(username):
                logger.bind(tag=TAG).warning(f"Registration attempt with existing username {username} from {request.remote}")
                return web.json_response({
                    'success': False,
                    'message': '用户名已存在'
                })

            # 创建用户
            user_data = {
                'username': username,
                'password': self.user_manager.hash_password(password),
                'devices': [],
                'created_at': datetime.datetime.now().isoformat(),
                'last_login': ''
            }
            await self.user_manager.add_user(username, user_data)

            logger.bind(tag=TAG).info(f"Successfully registered new user {username} from {request.remote}")
            return web.json_response({
                'success': True,
                'message': '注册成功'
            })

        except Exception as e:
            logger.bind(tag=TAG).error(f"Register error: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': '注册失败，请稍后重试'
            })
