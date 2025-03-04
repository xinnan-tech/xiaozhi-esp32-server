import time
from typing import Dict, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = 24 * 60 * 60  # 24小时过期
        
    def create_session(self, username: str) -> str:
        """创建新会话"""
        session_id = str(hash(f"{username}:{time.time()}"))
        self.sessions[session_id] = {
            'username': username,
            'created_at': time.time()
        }
        return session_id
        
    def validate_session(self, session_id: str) -> Optional[str]:
        """验证会话是否有效，返回用户名"""
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        if time.time() - session['created_at'] > self.session_timeout:
            del self.sessions[session_id]
            return None
            
        return session['username']
        
    def remove_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
