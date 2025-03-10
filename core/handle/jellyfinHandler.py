import json
from typing import Dict, List

import requests

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
from core.utils.util import seconds_to_time

TAG = __name__
logger = setup_logging()


def _extract_song_name(text):
    """从用户输入中提取歌名，可以使用llm中提取"""
    logger.bind(tag=TAG).debug(f"从用户输入中提取歌名: {text}")
    for keyword in ["听", "播放", "放", "唱"]:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip()
    return None

class JellyfinHandler:
    def __init__(self, config):
        self.config = config
        self.music_related_keywords = []

        if "music" in self.config:
            self.music_config = self.config["music"]
            self.jellyfin_endpoint = self.music_config['jellyfin']['endpoint']
            self.jellyfin_container = self.music_config['jellyfin']['container']
            self.jellyfin_api_key = self.music_config['jellyfin']['api_key']

            self.music_related_keywords = self.music_config.get("music_commands", [])
            self.music_ext = self.music_config.get("music_ext", (".mp3", ".wav", ".p3", ".m4a"))
        else:
            self.jellyfin_endpoint = os.path.abspath("./music")
            self.music_related_keywords = ["来一首歌", "唱一首歌", "播放音乐", "来点音乐", "背景音乐", "放首歌",
                                           "播放歌曲", "来点背景音乐", "我想听歌", "我要听歌", "放点音乐"]
            self.music_ext = (".mp3", ".wav", ".p3", ".m4a")

    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

        # 尝试匹配具体歌名
        if self.jellyfin_endpoint:
            potential_song = _extract_song_name(clean_text)
            if potential_song:
                best_match_item = self._find_best_match(potential_song)
                if best_match_item:
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {str(best_match_item)}")
                    await self.play_local_music(conn, stream_item=best_match_item)
                    return True
                else:
                    logger.bind(tag=TAG).debug(f"未找到匹配内容: {potential_song}")
            else:
                logger.bind(tag=TAG).debug(f"未找到潜在的音乐名[播放、听、唱、放]: {clean_text}")


        # 检查是否是通用播放音乐命令
        if any(cmd in clean_text for cmd in self.music_related_keywords):
            await self.play_local_music(conn)
            return True

        return False

    async def play_local_music(self, conn, stream_item=None):
        """
        播放本地音乐文件
        specific_file 歌曲对象
        """
        specific_file = stream_item['ItemId']
        song_name = stream_item['Name']
        music_path = None
        song_bytes = None
        dura_str = None
        try:
            # 确保路径正确性
            if specific_file:
                song_bytes = self.download_music_stream(specific_file)
                selected_music = specific_file
                dura_str = seconds_to_time(stream_item['RunTimeTicks']/10000000)
            else:
                selected_music = '中秋月.mp3'
                music_path = os.path.join(self.jellyfin_endpoint, selected_music)
                if not os.path.exists(music_path):
                    logger.bind(tag=TAG).error(f"选定的音乐文件不存在: {music_path}")
                    return
            text = f"正在播放{song_name}.mp3 {dura_str}"
            await send_stt_message(conn, text)
            conn.tts_first_text = song_name
            conn.tts_last_text = song_name
            conn.llm_finish_task = True
            if music_path and music_path.endswith(".p3"):
                opus_packets, duration = p3.decode_opus_from_file(music_path)
            else:
                opus_packets, duration = conn.tts.wav_stream_to_opus_data(song_bytes)
            conn.audio_play_queue.put((opus_packets, text))

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")

    def _find_best_match(self, potential_song):
        """查找最匹配的歌曲"""
        """返回item整个对象
        参数 potential_song 歌曲名称
        参数 music_files item_list
        """
        best_match = None
        highest_ratio = 0
        song_list = self.search_list(potential_song)

        for item in song_list:
            song_name = item['Name']
            ratio = difflib.SequenceMatcher(None, potential_song, song_name).ratio()
            if ratio > highest_ratio and ratio > 0.4:
                highest_ratio = ratio
                best_match = item
        return best_match

    def download_music_stream(self, item_id: str):
        """
        根据itemId下载stream
        return bytes
        """
        resp = requests.get(self.jellyfin_endpoint +f'/Audio/{item_id}/stream.{self.jellyfin_container}')
        if resp.status_code == 200:
            audio_bytes = b""
            for chunk in resp.iter_content(chunk_size=8192):
                audio_bytes += chunk
            logger.bind(tag=TAG).info(f"音频流已下载为字节数组，大小为 {len(audio_bytes)>>10} kb")
            return audio_bytes
        else:
            raise Exception(f"Failed to download audio file. Status code: {resp.status_code}")

    def search_list(self, term:str):
        """网络搜索歌曲
        [{
            "ItemId": "6ff65cc2ad6c211c92ba92a52cee10e0",
            "Id": "6ff65cc2ad6c211c92ba92a52cee10e0",
            "Name": "香水有毒-DJ",
            "Type": "Audio",
            "RunTimeTicks": 2935448576,
            "MediaType": "Audio",
            "Album": "Rendez-Vous: The Sound of the Mediterranean",
            "AlbumId": "2b9bc8f465a6d0e561f1ec633e2002df",
            "Artists": [],
            "ChannelId": null
        }]
        return List[Dict[str, str]]
        """
        resp = (
            requests.get(self.jellyfin_endpoint + f"/Search/Hints?api_key={self.jellyfin_api_key}&mediaTypes=Audio&searchTerm={term}"))
        if resp.status_code == 200:
            return json.loads(resp.content)['SearchHints']
        else:
            raise Exception(f"Failed to download audio file. Status code: {resp.status_code}")
