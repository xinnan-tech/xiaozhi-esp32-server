import os
import yaml
from config.logger import setup_logging
from aiohttp import web
from core.utils.util import get_project_dir
from config.private_config import PrivateConfig
from manager.api.user_manager import UserManager  # 添加导入
from core.utils.auth_code_gen import AuthCodeGenerator  # 添加导入

TAG = __name__
logger = setup_logging()

class ConfigHandler:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.user_manager = UserManager()  # 添加 user_manager 实例
        self.private_config_path = get_project_dir() + 'data/.private_config.yaml'
        self.config_path = get_project_dir() + 'config.yaml'
        # 如果存在.config.yaml文件，则使用该文件
        if os.path.exists(get_project_dir() + "data/.config.yaml"):
            self.config_path = get_project_dir() + "data/.config.yaml"
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    async def get_module_options(self, request):
        """Get all available module options from config.yaml"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Extract available modules
            modules = {
                'LLM': list(config.get('LLM', {}).keys()),
                'TTS': list(config.get('TTS', {}).keys()),
                'VAD': list(config.get('VAD', {}).keys()),
                'ASR': list(config.get('ASR', {}).keys())
            }
            
            return web.json_response({
                'success': True,
                'data': modules,
                'message': '获取成功'
            })

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error getting module options: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': '获取配置选项失败'
            })

    async def get_private_configs(self, request):
        """只返回用户绑定的设备配置"""
        try:
            username = request['username']
            logger.bind(tag=TAG).info(f"Getting devices for user: {username}")
            
            # 从用户管理器获取用户的设备列表
            user_devices = await self.user_manager.get_user_devices(username)
            logger.bind(tag=TAG).info(f"User {username} has devices: {user_devices}")
            
            # 读取所有配置
            all_configs = {}
            if os.path.exists(self.private_config_path):
                with open(self.private_config_path, 'r', encoding='utf-8') as f:
                    all_configs = yaml.safe_load(f) or {}
            
            # 只返回用户有权限的设备配置
            user_configs = {
                device_id: config 
                for device_id, config in all_configs.items()
                if device_id in user_devices
            }
            
            logger.bind(tag=TAG).info(f"Returning {len(user_configs)} device configs for user {username}")
            return web.json_response({
                'success': True,
                'data': user_configs,
                'message': '获取成功'
            })
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error getting devices for user {request.get('username')}: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': f'获取设备列表失败: {str(e)}'
            }, status=400)

    async def save_device_config(self, request):
        """保存单个设备的配置"""
        try:
            data = await request.json()
            device_id = data.get('id')
            config = data.get('config')
            username = request['username']  # 从请求中获取用户名

            # 检查设备所有权
            user_devices = await self.user_manager.get_user_devices(username)
            if device_id not in user_devices:
                return web.json_response({
                    'success': False,
                    'message': '无权操作此设备'
                }, status=403)

            logger.bind(tag=TAG).info(f"Device config updated: {device_id} :\n{config}")
            if not device_id or not config:
                return web.json_response({
                    'success': False,
                    'message': '设备ID和配置不能为空'
                })

            # 使用PrivateConfig处理配置保存
            private_config = PrivateConfig(device_id, self.config)
            await private_config.load_or_create()
            
            success = await private_config.update_config(
                config.get('selected_module'),
                config.get('prompt'),
                config.get('nickname', '小智')
            )
            

            if not success:
                raise Exception("Failed to update device config")

            return web.json_response({
                'success': True,
                'message': '保存成功'
            })

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error saving device config: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': f'保存配置失败: {str(e)}'
            })

    async def delete_device_config(self, request):
        """删除设备配置"""
        try:
            data = await request.json()
            device_id = data.get('device_id')
            username = request['username']

            # 检查设备所有权
            user_devices = await self.user_manager.get_user_devices(username)
            if device_id not in user_devices:
                return web.json_response({
                    'success': False,
                    'message': '无权删除此设备'
                }, status=403)

            # 使用PrivateConfig处理配置删除
            private_config = PrivateConfig(device_id, self.config)
            success = await private_config.delete_config()
            await self.user_manager.remove_device(username, device_id)

            if not success:
                raise Exception("Failed to delete device config")

            return web.json_response({
                'success': True,
                'message': '删除成功'
            })

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error deleting device config: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': f'删除配置失败: {str(e)}'
            })

    async def bind_device(self, request):
        """绑定设备到用户"""
        try:
            data = await request.json()
            auth_code = data.get('auth_code')
            username = request['username']

            if not auth_code or len(auth_code) != 6:
                return web.json_response({
                    'success': False,
                    'message': '请输入6位认证码'
                }, status=400)

            # 读取所有设备配置
            with open(self.private_config_path, 'r', encoding='utf-8') as f:
                all_configs = yaml.safe_load(f) or {}

            # 查找匹配认证码的设备
            device_found = None
            for device_id, config in all_configs.items():
                if config.get('auth_code') == auth_code and not config.get('owner'):
                    device_found = device_id
                    break

            if not device_found:
                return web.json_response({
                    'success': False,
                    'message': '认证码无效或设备已被绑定'
                }, status=400)

            # 使用 PrivateConfig 进行绑定
            private_config = PrivateConfig(device_found, self.config, AuthCodeGenerator())
            await private_config.load_or_create()
            
            # 绑定设备到用户 - 修改为异步调用
            success = await private_config.bind_user(username)
            if success:
                # 同时更新用户的设备列表 - 修改为异步调用
                await self.user_manager.add_device(username, device_found)
                return web.json_response({
                    'success': True,
                    'message': '设备绑定成功'
                })
            else:
                return web.json_response({
                    'success': False,
                    'message': '设备绑定失败'
                }, status=500)

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error binding device: {str(e)}", exc_info=True)
            return web.json_response({
                'success': False,
                'message': f'绑定设备失败: {str(e)}'
            }, status=500)
