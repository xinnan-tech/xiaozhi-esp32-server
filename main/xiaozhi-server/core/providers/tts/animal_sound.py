import os
import queue
from typing import Dict, List

from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    """
    通过情绪标签播放预置的动物叫声。
    适用于“动物互动”模式：LLM 返回情绪词（如 开心/悲伤/生气/害怕/无奈/撒娇），
    本 TTS 直接选择对应音频文件推送给客户端，而不做文字合成。
    """

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.base_path = config.get("base_path", "config/assets/animal_sounds")
        # emotion -> filename 映射；支持 default 兜底
        self.emotion_files: Dict[str, str] = config.get("emotion_files", {})
        self.default_file = config.get("default_file")
        self.keyword_map: Dict[str, List[str]] = config.get(
            "emotion_keywords",
            {
                "happy": ["开心", "高兴", "快乐", "喜悦"],
                "sad": ["悲伤", "难过", "伤心", "沮丧"],
                "angry": ["生气", "愤怒", "气愤"],
                "afraid": ["害怕", "恐惧", "紧张"],
                "helpless": ["无奈", "唉", "叹气"],
                "coquetry": ["撒娇", "卖萌", "黏人"],
            },
        )
        self._session_started = False

    async def text_to_speak(self, text, output_file):
        """
        动物叫声模式不做 TTS 合成，直接使用预置音频。
        保留空实现以兼容基类接口。
        """
        return None

    def tts_text_priority_thread(self):
        """
        将文本情绪映射为音频文件并推送到播放队列。
        """
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)

                if message.sentence_type == SentenceType.FIRST:
                    # 新一句开始，重置状态
                    self.conn.client_abort = False
                    self._session_started = False
                    self.tts_audio_first_sentence = True
                    continue

                if self.conn.client_abort:
                    continue

                if message.content_type == ContentType.TEXT:
                    emotion = self._detect_emotion(message.content_detail or "")
                    audio_path = self._resolve_audio_path(emotion)
                    label_for_log = emotion or (message.content_detail or "")

                    # 发送开场标记，便于客户端识别一句话的开始
                    if not self._session_started:
                        self.tts_audio_queue.put(
                            (SentenceType.FIRST, None, label_for_log)
                        )
                        self._session_started = True

                    if audio_path and os.path.exists(audio_path):
                        logger.bind(tag=TAG).info(
                            f"动物音频播放: emotion={emotion}, file={audio_path}"
                        )
                        self._process_audio_file_stream(
                            audio_path, callback=self.handle_opus
                        )
                    else:
                        logger.bind(tag=TAG).warning(
                            f"未找到对应的动物音频，emotion={emotion}, path={audio_path}"
                        )
                        # 即使找不到音频，也要发送一个空的音频数据，避免客户端等待
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, b"", label_for_log)
                        )

                elif message.content_type == ContentType.FILE:
                    # 处理文件类型的消息
                    if message.content_file and os.path.exists(message.content_file):
                        logger.bind(tag=TAG).info(
                            f"播放音频文件: {message.content_file}"
                        )
                        if not self._session_started:
                            self.tts_audio_queue.put(
                                (SentenceType.FIRST, None, message.content_detail or "")
                            )
                            self._session_started = True
                        self._process_audio_file_stream(
                            message.content_file, callback=self.handle_opus
                        )

                if message.sentence_type == SentenceType.LAST:
                    # 一句话结束
                    self.tts_audio_queue.put(
                        (SentenceType.LAST, [], message.content_detail or "")
                    )
                    self._session_started = False

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"动物音频处理失败: {e.__class__.__name__}, {e}"
                )

    def _detect_emotion(self, text: str) -> str:
        """根据关键词粗略匹配情绪标签"""
        for emotion, keywords in self.keyword_map.items():
            if any(k in text for k in keywords):
                return emotion
        return "default"

    def _resolve_audio_path(self, emotion: str) -> str:
        filename = self.emotion_files.get(emotion) or self.emotion_files.get("default")
        if not filename and self.default_file:
            filename = self.default_file
        if not filename:
            return ""
        return filename if os.path.isabs(filename) else os.path.join(self.base_path, filename)

