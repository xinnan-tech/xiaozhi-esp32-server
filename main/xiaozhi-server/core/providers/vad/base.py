from abc import ABC, abstractmethod


class VADProviderBase(ABC):
    @abstractmethod
    def is_vad(self, conn, data) -> bool:
        """检测音频数据中的语音活动"""
        pass
    
    @abstractmethod
    def is_eou(self, conn, text) -> bool:
        """End of Utterance（话语结束检测），是基于语义理解的自动判断用户发言是否结束的技术, True 表示结束，False 表示未结束"""
        pass
    
    @abstractmethod
    def get_silence_duration(self, conn) -> int:
        """返回语音静音时长，单位ms"""
        pass
