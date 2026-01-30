"""
SharedASRProxy: 共享 ASR 管理器的代理类

功能：
- 包装 SharedASRManager
- 提供与原 ASR Provider 相同的接口
- 处理队列满等异常情况
"""

from typing import List, Tuple, Optional, Dict, Any
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__


class SharedASRProxy(ASRProviderBase):
    """
    共享 ASR 管理器的代理类
    
    该类提供与原 ASR Provider 相同的接口，
    但实际推理工作由 SharedASRManager 完成。
    """
    
    def __init__(self, manager):
        """
        初始化代理
        
        Args:
            manager: SharedASRManager 实例
        """
        super().__init__()
        self.manager = manager
        
        # 从共享管理器获取接口类型
        if manager.model_instance and hasattr(manager.model_instance, 'interface_type'):
            self.interface_type = manager.model_instance.interface_type
        else:
            self.interface_type = InterfaceType.LOCAL
        
        logger.bind(tag=TAG).info("SharedASRProxy 初始化完成")
    
    async def speech_to_text(
        self, 
        opus_data: List[bytes], 
        session_id: str, 
        audio_format: str = "opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        语音转文本（通过共享管理器）
        
        Args:
            opus_data: 音频数据（Opus 编码的字节列表）
            session_id: 会话 ID
            audio_format: 音频格式，默认 "opus"
            
        Returns:
            Tuple[str, str]: (识别的文本, 音频文件路径)
        """
        try:
            # 检查管理器状态
            if not self.manager.is_ready():
                logger.bind(tag=TAG).error("ASR 管理器未就绪")
                return "", None
            
            # 提交任务到共享管理器
            result = await self.manager.submit_task(
                opus_data, 
                session_id, 
                audio_format
            )
            
            return result
            
        except RuntimeError as e:
            # 队列满或服务未运行
            logger.bind(tag=TAG).warning(f"ASR 服务繁忙: {e}")
            # 返回友好提示，而不是空字符串
            return "服务繁忙，请稍后重试", None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR 推理失败: {e}")
            return "", None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            队列状态字典
        """
        return self.manager.get_queue_status()
    
    def is_ready(self) -> bool:
        """
        检查代理是否就绪
        
        Returns:
            是否就绪
        """
        return self.manager.is_ready()
    
    async def close(self):
        """
        关闭代理
        
        注意：不关闭共享管理器，由服务器统一管理
        """
        logger.bind(tag=TAG).debug("SharedASRProxy 关闭")
        # 代理不负责关闭共享管理器
        pass

