from config.logger import setup_logging
import json
import asyncio
import os
import random
import difflib
import re
import traceback
import threading
import websockets

TAG = __name__
logger = setup_logging()


class MusicHandler:
    def __init__(self, config):
        self.config = config
        self.music_related_keywords = []

        if "music" in self.config:
            self.music_config = self.config["music"]
            self.music_dir = os.path.abspath(
                self.music_config.get("music_dir", "./music")  # 默认路径修改
            )
            self.music_related_keywords = self.music_config.get("music_commands", [])
        else:
            self.music_dir = os.path.abspath("./music")
            self.music_related_keywords = ["来一首歌", "唱一首歌", "播放音乐", "来点音乐", "背景音乐", "放首歌",
                                           "播放歌曲", "来点背景音乐", "我想听歌", "我要听歌", "放点音乐"]

        self.is_playing = False
        self.stop_event = threading.Event()

    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

        # 尝试匹配具体歌名
        if os.path.exists(self.music_dir):
            music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
            logger.bind(tag=TAG).debug(f"找到的音乐文件: {music_files}")

            potential_song = self._extract_song_name(clean_text)
            if potential_song:
                best_match = self._find_best_match(potential_song, music_files)
                if best_match:
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")
                    await self.play_local_music(conn, specific_file=best_match)
                    return True

        # 检查是否是通用播放音乐命令
        if any(cmd in clean_text for cmd in self.music_related_keywords):
            await self.play_local_music(conn)
            return True

        return False

    def _extract_song_name(self, text):
        """从用户输入中提取歌名"""
        for keyword in ["听", "播放", "放", "唱"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[1].strip()
        return None

    def _find_best_match(self, potential_song, music_files):
        """查找最匹配的歌曲"""
        best_match = None
        highest_ratio = 0

        for music_file in music_files:
            song_name = os.path.splitext(music_file)[0]
            ratio = difflib.SequenceMatcher(None, potential_song, song_name).ratio()
            if ratio > highest_ratio and ratio > 0.4:
                highest_ratio = ratio
                best_match = music_file
        return best_match

    async def play_local_music(self, conn, specific_file=None):
        """播放本地音乐文件"""
        try:
            if not os.path.exists(self.music_dir):
                logger.bind(tag=TAG).error(f"音乐目录不存在: {self.music_dir}")
                return

            # 确保路径正确性
            if specific_file:
                music_path = os.path.join(self.music_dir, specific_file)
                if not os.path.exists(music_path):
                    logger.bind(tag=TAG).error(f"指定的音乐文件不存在: {music_path}")
                    return
                selected_music = specific_file
            else:
                music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
                if not music_files:
                    logger.bind(tag=TAG).error("未找到MP3音乐文件")
                    return
                selected_music = random.choice(music_files)
                music_path = os.path.join(self.music_dir, selected_music)

            await self._send_music_stream(conn, music_path, selected_music)

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")

    async def _send_music_stream(self, conn, music_path, selected_music):
        """播放音乐流"""
        try:
            # 发送开始消息
            await self._send_tts_message(conn, "start")
            await self._send_tts_message(conn, "sentence_start", f"正在播放：{selected_music.replace('.mp3', '')}")

            conn.is_playing_music = True

            # 转换并发送音频数据
            opus_packets, duration = conn.tts.wav_to_opus_data(music_path)
            packet_duration = (duration * 1000) / len(opus_packets)

            await self._send_tts_message(conn, "sentence_end")
            await self._send_tts_message(conn, "sentence_start", selected_music)

            await self._stream_audio_packets(conn, opus_packets, packet_duration)

            await self._send_tts_message(conn, "sentence_end")

        except Exception as e:
            logger.bind(tag=TAG).error(f"音乐流发送失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
        finally:
            conn.is_playing_music = False
            await self._send_tts_message(conn, "stop")

    async def _stream_audio_packets(self, conn, opus_packets, packet_duration):
        """流式发送音频数据包"""
        self.is_playing = True
        self.stop_event.clear()
        self.current_opus_packets = opus_packets  # 存储当前数据包

        try:
            # 将流式任务保存为实例属性
            self._current_stream_task = asyncio.current_task()

            # TODO 对发送音频进行流控，以避免过快的网络传输导致的卡顿
            for i, opus_packet in enumerate(opus_packets):
                if self.stop_event.is_set():
                    # 如果被中断，先发送停止消息再退出
                    if hasattr(conn, 'websocket') and hasattr(conn.websocket, 'send'):
                        try:
                            await self._send_tts_message(conn, "stop")
                        except:
                            pass
                    break
                await conn.websocket.send(opus_packet)
            logger.bind(tag=TAG).info("发送完毕")
        except asyncio.CancelledError:
            logger.bind(tag=TAG).info("音乐播放被强制取消")
        finally:
            self.is_playing = False
            # 移除finally块中的停止消息发送，因为已经在中断时发送过了

    async def _send_tts_message(self, conn, state, text=None):
        """发送TTS状态消息"""
        if not hasattr(conn, 'websocket') or not hasattr(conn.websocket, 'send'):
            return

        message = {
            "type": "tts",
            "state": state,
            "session_id": conn.session_id
        }
        if text is not None:
            message["text"] = text
        try:
            await conn.websocket.send(json.dumps(message))
        except (websockets.exceptions.ConnectionClosed, ConnectionError):
            logger.bind(tag=TAG).warning("发送TTS消息时连接已关闭")

    def stop_playing(self):
        """停止音乐播放"""
        self.stop_event.set()
        self.is_playing = False

        # 增强中断可靠性
        if hasattr(self, '_current_stream_task'):
            try:
                if not self._current_stream_task.done():
                    self._current_stream_task.cancel()
                    logger.bind(tag=TAG).debug("成功取消流式任务")
            except Exception as e:
                logger.bind(tag=TAG).error(f"取消流式任务失败: {str(e)}")

        # 清空播放队列并重置状态
        self.current_opus_packets = []
        logger.bind(tag=TAG).info("音乐播放已强制终止")
