from config.logger import setup_logging
import os
import random
import difflib
import re
import traceback
from core.handle.sendAudioHandle import sendAudioMessage, send_stt_message

TAG = __name__
logger = setup_logging()


def _extract_song_name(text):
    """从用户输入中提取歌名"""
    for keyword in ["听", "播放", "放", "唱"]:
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

    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

        # 尝试匹配具体歌名
        if os.path.exists(self.music_dir):
            music_files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
            logger.bind(tag=TAG).debug(f"找到的音乐文件: {music_files}")

            potential_song = _extract_song_name(clean_text)
            if potential_song:
                best_match = _find_best_match(potential_song, music_files)
                if best_match:
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")
                    await self.play_local_music(conn, specific_file=best_match)
                    return True

        # 检查是否是通用播放音乐命令
        if any(cmd in clean_text for cmd in self.music_related_keywords):
            await self.play_local_music(conn)
            return True

        return False

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
            text = f"正在播放{selected_music}"
            await send_stt_message(conn, text)
            conn.tts_first_text = selected_music
            conn.tts_last_text = selected_music
            conn.llm_finish_task = True
            opus_packets, duration = conn.tts.wav_to_opus_data(music_path)
            await sendAudioMessage(conn, opus_packets, duration, selected_music)

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
