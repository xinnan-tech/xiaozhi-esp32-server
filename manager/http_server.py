# 添加项目根目录到Python路径
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from config.logger import setup_logging
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions
from manager.api.login import LoginHandler
from manager.api.register import RegisterHandler
from manager.api.user_manager import UserManager
from manager.api.config import ConfigHandler
from manager.session import SessionManager
from functools import wraps

TAG = __name__
logger = setup_logging()

def auth_required(handler):
    """鉴权装饰器"""
    @wraps(handler)
    async def wrapper(self, request):
        session_id = request.cookies.get('session_id')
        username = self.session_manager.validate_session(session_id)
        if not username:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        # 将用户名添加到请求对象
        request['username'] = username
        return await handler(self, request)
    return wrapper

class WebUI:
    def __init__(self):
        self.app = web.Application()
        self.user_manager = UserManager()
        self.session_manager = SessionManager()
        
        # 添加静态文件路径
        self.static_path = os.path.join(root_dir, 'ZhiKongTaiWeb', 'dist')
        
        self.setup_routes()
        self.setup_cors()

    def setup_cors(self):
        """设置CORS"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)

    def setup_routes(self):
        """设置路由"""
        login_handler = LoginHandler(self.user_manager, self.session_manager)
        register_handler = RegisterHandler(self.user_manager)
        config_handler = ConfigHandler(self.session_manager)
        
        # Public APIs
        self.app.router.add_post('/api/login', login_handler.handle_login)
        self.app.router.add_post('/api/register', register_handler.handle_register)

        # Protected APIs
        self.app.router.add_get('/api/config/devices', self.auth_wrapper(config_handler.get_private_configs))

        self.app.router.add_get('/api/config/module-options', self.auth_wrapper(config_handler.get_module_options))
        self.app.router.add_post('/api/config/save_device_config', self.auth_wrapper(config_handler.save_device_config))
        self.app.router.add_post('/api/config/delete_device', self.auth_wrapper(config_handler.delete_device_config))
        self.app.router.add_post('/api/config/bind_device', self.auth_wrapper(config_handler.bind_device))

        # 添加静态文件服务
        self.app.router.add_static('/assets/', path=os.path.join(self.static_path, 'assets'))
        # 所有未匹配的路由都返回 index.html
        self.app.router.add_get('/{tail:.*}', self.handle_static_files)

    async def handle_static_files(self, request):
        """处理静态文件请求，支持SPA前端路由"""
        index_file = os.path.join(self.static_path, 'index.html')
        if os.path.exists(index_file):
            return web.FileResponse(index_file)
        return web.Response(status=404, text='Not found')

    def auth_wrapper(self, handler):
        """包装处理器添加鉴权"""
        @wraps(handler)
        async def wrapper(request):
            # 从请求头获取session_id
            session_id = request.headers.get('Authorization')
            if not session_id:
                logger.bind(tag=TAG).warning("No session_id in Authorization header")
                return web.json_response({'error': 'Unauthorized'}, status=401)

            username = self.session_manager.validate_session(session_id)
            if not username:
                logger.bind(tag=TAG).warning(f"Invalid session_id: {session_id}")
                return web.json_response({'error': 'Unauthorized'}, status=401)
                
            request['username'] = username
            logger.bind(tag=TAG).debug(f"Auth success for user: {username}")
            return await handler(request)
        return wrapper

    def run(self, host='0.0.0.0', port=8002):
        """运行服务器"""
        web.run_app(self.app, host=host, port=port)

if __name__ == '__main__':
    webui = WebUI()
    webui.run()
