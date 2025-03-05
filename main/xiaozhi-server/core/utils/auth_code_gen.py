import random
import threading
import time
from typing import Set

class AuthCodeGenerator:
    _instance = None
    _instance_lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = super(AuthCodeGenerator, cls).__new__(cls)
                    # 初始化随机种子
                    random.seed(time.time())
        return cls._instance

    def __init__(self):
        # 确保 __init__ 只被调用一次
        if not hasattr(self, '_initialized'):
            self._used_codes: Set[str] = set()
            self._code_timestamps = {}
            self._lock = threading.Lock()
            self._code_timeout = 3 * 24 * 60 * 60
            self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """获取AuthCodeGenerator的单例实例"""
        return cls()

    def generate_code(self) -> str:
        """
        生成6位数字认证码，确保不重复
        返回: 6位数字字符串
        """
        with self._lock:
            self._clean_expired_codes()  # 清理过期code
            while True:
                # 使用时间戳和已用码数量作为种子，确保每次生成不同的随机数
                seed = int(time.time() * 1000) + len(self._used_codes)
                random.seed(seed)
                
                # 生成6位随机数字
                code = ''.join(str(random.randint(0, 9)) for _ in range(6))
                
                # 检查是否已存在
                if code not in self._used_codes:
                    self._used_codes.add(code)
                    self._code_timestamps[code] = time.time()
                    return code
    
    def remove_code(self, code: str) -> bool:
        """
        删除已使用的认证码
        参数:
            code: 要删除的认证码
        返回:
            bool: 删除成功返回True，码不存在返回False
        """
        print('remove_code', code)
        with self._lock:
            if code in self._used_codes:
                self._used_codes.remove(code)
                if code in self._code_timestamps:
                    del self._code_timestamps[code]
                return True
            return False
    
    def is_code_used(self, code: str) -> bool:
        """
        检查认证码是否已被使用
        参数:
            code: 要检查的认证码
        返回:
            bool: 如果码存在返回True，否则返回False
        """
        with self._lock:
            return code in self._used_codes
    
    def clear_codes(self):
        """清空所有已使用的认证码"""
        with self._lock:
            self._used_codes.clear()
            self._code_timestamps.clear()
    
    def _clean_expired_codes(self):
        """清理过期的认证码"""
        current_time = time.time()
        expired_codes = [
            code for code, timestamp in self._code_timestamps.items()
            if (current_time - timestamp) > self._code_timeout
        ]
        for code in expired_codes:
            self._used_codes.remove(code)
            del self._code_timestamps[code]
