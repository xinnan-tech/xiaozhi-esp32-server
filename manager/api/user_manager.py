import os
import yaml
import hashlib
from config.logger import setup_logging
from core.utils.util import get_project_dir
from core.utils.lock_manager import FileLockManager

TAG = __name__
logger = setup_logging()

class UserManager:
    def __init__(self):
        self.secrets_path = get_project_dir() + 'data/.secrets.yaml'
        self.lock_manager = FileLockManager()
        self.ensure_secrets_file()

    def ensure_secrets_file(self):
        """确保 .secrets.yaml 文件存在"""
        if not os.path.exists(self.secrets_path):
            default_config = {
                'users': {}
            }
            try:
                with open(self.secrets_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f)
                os.chmod(self.secrets_path, 0o600)
                logger.bind(tag=TAG).info("Created new .secrets.yaml file")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to create .secrets.yaml: {e}")
                raise
    
    async def _load_user_data_internal(self):
        """内部加载用户数据方法 - 不获取锁"""
        try:
            with open(self.secrets_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {'users': {}}
                users = data['users']
                logger.bind(tag=TAG).debug("Successfully loaded user data")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load user data: {e}")
            users = {}
        return users
    
    async def load_user_data(self):
        """加载用户数据"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                users = await self._load_user_data_internal()
            finally:
                self.lock_manager.release_lock(self.secrets_path)
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load user data: {e}")
            users = {}
        return users

    async def _save_user_data_internal(self, users):
        """内部保存用户数据方法 - 不获取锁"""
        try:
            with open(self.secrets_path, 'w', encoding='utf-8') as f:
                yaml.dump({'users': users}, f)
            logger.bind(tag=TAG).debug("Successfully saved user data")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to save user data: {e}")
            raise

    async def save_user_data(self, users):
        """外部保存用户数据方法 - 获取锁"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                await self._save_user_data_internal(users)
            finally:
                self.lock_manager.release_lock(self.secrets_path)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to save user data: {e}")
            raise

    def hash_password(self, password):
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    async def get_users(self):
        """异步获取所有用户"""
        users = await self.load_user_data()  # 确保获取最新数据
        return users

    async def get_user(self, username):
        """异步获取指定用户"""
        users = await self.load_user_data()  # 确保获取最新数据
        return users.get(username)

    async def add_user(self, username: str, user_data: dict):
        """异步添加新用户"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                users = await self._load_user_data_internal()  # 确保获取最新数据
                if username in users:
                    raise ValueError("User already exists")
                users[username] = user_data
                await self._save_user_data_internal(users)
            finally:
                self.lock_manager.release_lock(self.secrets_path)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error adding user: {e}")
            raise

    async def update_user(self, username, data):
        """更新用户数据"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                users = await self._load_user_data_internal()  # 确保获取最新数据
                if username in users:
                    users[username].update(data)
                    await self._save_user_data_internal(users)
                    return True
                return False
            finally:
                self.lock_manager.release_lock(self.secrets_path)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error updating user: {e}")
            return False

    async def get_user_devices(self, username: str) -> list:
        """获取用户的设备列表"""
        user = await self.get_user(username)
        print(user)
        if user and user.get('devices'):
            return user['devices']
        return []

    async def add_device(self, username: str, device_id: str) -> bool:
        """添加设备到用户的设备列表"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                users = await self._load_user_data_internal()  # 确保获取最新数据
                user = users.get(username)  # 直接从内存获取，因为已经有锁
                if not user:
                    return False

                if 'devices' not in user:
                    user['devices'] = []

                if device_id not in user['devices']:
                    user['devices'].append(device_id)
                    await self._save_user_data_internal(users)
                return True
            finally:
                self.lock_manager.release_lock(self.secrets_path)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error adding device: {e}")
            return False

    async def remove_device(self, username: str, device_id: str) -> bool:
        """从用户的设备列表中移除设备"""
        try:
            await self.lock_manager.acquire_lock(self.secrets_path)
            try:
                users = await self._load_user_data_internal()  # 确保获取最新数据
                user = users.get(username)  # 直接从内存获取，因为已经有锁
                if user and 'devices' in user:
                    if device_id in user['devices']:
                        user['devices'].remove(device_id)
                        await self._save_user_data_internal(users)
                        return True
                return False
            finally:
                self.lock_manager.release_lock(self.secrets_path)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error removing device: {e}")
            return False
