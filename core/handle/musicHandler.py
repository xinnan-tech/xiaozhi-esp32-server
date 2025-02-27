from config.logger import setup_logging
import os
import requests
from pydub import AudioSegment
import random
import difflib
import re
import traceback
from core.handle.sendAudioHandle import sendAudioMessage, send_stt_message

TAG = __name__
logger = setup_logging()


def _extract_song_name(text):
    """从用户输入中提取歌名"""
    for keyword in ["听", "播放", "放", "唱", "点歌"]:
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
        self.online_music_related_keywords = [] # 在线播放
        # 新增在线音乐相关配置
        self.music_cache_dir = os.path.abspath("./music/cache")
        os.makedirs(self.music_cache_dir, exist_ok=True)
        self.download_api = "http://datukuai.top:1450/djs/API/QQ_Music/api.php"

        if "music" in self.config:
            self.music_config = self.config["music"]
            self.music_dir = os.path.abspath(
                self.music_config.get("music_dir", "./music")  # 默认路径修改
            )
            self.music_related_keywords = self.music_config.get("music_commands", [])
            self.online_music_related_keywords = self.music_config.get("online_commands", [])
        else:
            self.music_dir = os.path.abspath("./music")
            self.music_related_keywords = ["来一首歌", "唱一首歌", "播放音乐", "来点音乐", "背景音乐", "放首歌",
                                           "播放歌曲", "来点背景音乐", "我想听歌", "我要听歌", "放点音乐"]
            self.online_music_related_keywords = ["点歌", "在线播放"]


    async def handle_online_song_command(self, conn, song_name):
        """处理在线点歌指令"""
        try:
            # 调用QQ音乐API获取歌曲链接
            response = requests.get(self.download_api, params={'msg': song_name, 'n': 1}, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.bind(tag=TAG).info(f"点歌API响应: {data}")
            error_code = data.get('code')

            if error_code != 1:
                if error_code == -4:
                    error_details = data.get('text', '')
                    logger.bind(tag=TAG).info(error_details)
                    await send_stt_message(conn, "播放失败，该歌曲可能是会员专享歌曲。")
                    return False
                elif error_code == -1:
                    error_details = data.get('text', '')
                    logger.bind(tag=TAG).info(error_details)
                    await send_stt_message(conn, error_details)
                    return False
                else:
                    await send_stt_message(conn, "在线点歌API发生错误")
                    raise Exception(f"API错误: {data['text']}")

            # 信息同步
            text = f"开始播放在线歌曲: {song_name}"
            await send_stt_message(conn, text)

            music_url = data['data']['music']
            # 新增：优先使用API返回的标准歌曲名
            api_song_name = data['data'].get('song', '')  # 正式名称
            song_name = api_song_name or _extract_song_name(song_name)  # 备用本地提取
            
            # 规范化文件名
            file_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_]', '', song_name)  # 移除非中文、字母、数字和下划线
            file_name = file_name.strip() or os.path.basename(music_url)  # 防止空名
            file_extension = os.path.splitext(music_url)[1]  # 保留原始扩展名
            cache_path = os.path.join(self.music_cache_dir, f"{file_name}{file_extension}")

            # 下载歌曲文件
            response = requests.get(music_url, stream=True, timeout=10)
            response.raise_for_status()
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 转换为MP3格式
            mp3_path = self.convert_to_mp3(cache_path)
            if not mp3_path:
                raise Exception("转换失败")

            # 播放转换后的MP3文件
            await self.play_online_music(conn, specific_file=mp3_path, song_name=file_name)
            
        except Exception as e:
            await send_stt_message(conn, f"在线点歌失败: {str(e)}")
            logger.bind(tag=TAG).error(f"在线点歌失败: {e}")
            return False

    def convert_to_mp3(self, input_path):
        """将音频文件转换为MP3格式"""
        try:
            if not input_path.endswith('.m4a'):
                if input_path.endswith('.mp3'):
                    return input_path
                else:
                    raise ValueError(f"不支持格式: {os.path.splitext(input_path)[1]}")
            
            audio = AudioSegment.from_file(input_path, format='m4a')
            output_path = os.path.splitext(input_path)[0] + '.mp3'
            audio.export(output_path, format='mp3', bitrate='192k')
            logger.bind(tag=TAG).info(f"转换成功: {input_path} → {output_path}")
            return output_path
        except Exception as e:
            logger.bind(tag=TAG).error(f"转换错误: {str(e)}")
            return None
                
    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = text.strip()  # 移除不必要的字符清洗
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

        # 在线播放
        if any(cmd in clean_text for cmd in self.online_music_related_keywords):
            # 调用在线点歌处理
            song_name = _extract_song_name(clean_text)
            await self.handle_online_song_command(conn, song_name)
            return True

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
                
        # 本地播放
        if any(cmd in clean_text for cmd in self.music_related_keywords):
            await self.play_local_music(conn)
            return True

        return False

    async def play_online_music(self, conn, specific_file=None, song_name=None):
        """播放在线音乐文件"""
        try:
            selected_music = specific_file
            music_path = os.path.join(self.music_dir, selected_music)
            conn.tts_first_text = selected_music
            conn.tts_last_text = selected_music
            conn.llm_finish_task = True
            opus_packets, duration = conn.tts.wav_to_opus_data(music_path)
            status = f"正在播放歌曲: {song_name}"
            text = f"《{song_name}》"
            logger.bind(tag=TAG).info(status)
            await sendAudioMessage(conn, opus_packets, duration, text)

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放在线音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")

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
