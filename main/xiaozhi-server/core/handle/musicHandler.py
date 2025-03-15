from config.logger import setup_logging
import os
import random
import difflib
import re
import traceback
from pathlib import Path
import time
from core.handle.sendAudioHandle import send_stt_message
from core.utils import p3

TAG = __name__
logger = setup_logging()


def _extract_song_name(text):
    """从用户输入中提取歌名"""
    for keyword in ["播放音乐"]:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip()
    return None


def _find_best_match(potential_song, music_files):
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


class MusicManager:
    def __init__(self, music_dir, music_ext):
        self.music_dir = Path(music_dir)
        self.music_ext = music_ext

    def get_music_files(self):
        music_files = []
        for file in self.music_dir.rglob("*"):
            # 判断是否是文件
            if file.is_file():
                # 获取文件扩展名
                ext = file.suffix.lower()
                # 判断扩展名是否在列表中
                if ext in self.music_ext:
                    # music_files.append(str(file.resolve()))  # 添加绝对路径
                    # 添加相对路径
                    music_files.append(str(file.relative_to(self.music_dir)))
        return music_files


class MusicHandler:
    def __init__(self, config):
        self.config = config

        if "music" in self.config:
            self.music_config = self.config["music"]
            self.music_dir = os.path.abspath(
                self.music_config.get("music_dir", "./music")  # 默认路径修改
            )
            self.music_ext = self.music_config.get("music_ext", (".mp3", ".wav", ".p3"))
            self.refresh_time = self.music_config.get("refresh_time", 60)
        else:
            self.music_dir = os.path.abspath("./music")
            self.music_ext = (".mp3", ".wav", ".p3")
            self.refresh_time = 60

        # 获取音乐文件列表
        self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
        self.scan_time = time.time()
        logger.bind(tag=TAG).debug(f"找到的音乐文件: {self.music_files}")

    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

        # 尝试匹配具体歌名
        if os.path.exists(self.music_dir):
            if time.time() - self.scan_time > self.refresh_time:
                # 刷新音乐文件列表
                self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
                self.scan_time = time.time()
                logger.bind(tag=TAG).debug(f"刷新的音乐文件: {self.music_files}")

            potential_song = _extract_song_name(clean_text)
            if potential_song:
                best_match = _find_best_match(potential_song, self.music_files)
                if best_match:
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")
                    await self.play_local_music(conn, specific_file=best_match)
                    return True
        # 检查是否是通用播放音乐命令
        await self.play_local_music(conn)
        return True

    async def play_local_music(self, conn, specific_file=None):
        """播放本地音乐文件"""
        try:
            if not os.path.exists(self.music_dir):
                logger.bind(tag=TAG).error(f"音乐目录不存在: {self.music_dir}")
                return

            # 确保路径正确性
            if specific_file:
                selected_music = specific_file
                music_path = os.path.join(self.music_dir, specific_file)
            else:
                if not self.music_files:
                    logger.bind(tag=TAG).error("未找到MP3音乐文件")
                    return
                selected_music = random.choice(self.music_files)
                music_path = os.path.join(self.music_dir, selected_music)

            if not os.path.exists(music_path):
                logger.bind(tag=TAG).error(f"选定的音乐文件不存在: {music_path}")
                return
            text = f"正在播放{selected_music}"
            await send_stt_message(conn, text)
            conn.tts_first_text_index = 0
            conn.tts_last_text_index = 0
            conn.llm_finish_task = True
            if music_path.endswith(".p3"):
                opus_packets, duration = p3.decode_opus_from_file(music_path)
            else:
                opus_packets, duration = conn.tts.audio_to_opus_data(music_path)
            conn.audio_play_queue.put((opus_packets, selected_music, 0))

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")