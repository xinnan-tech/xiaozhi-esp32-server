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

import urllib.request
import urllib.parse
urllib.request.socket.setdefaulttimeout(10)
import requests
import io
from threading import Thread, Event
from queue import Queue
import struct
from pydub import AudioSegment
import miniaudio
import json
import sys
import opuslib_next

TAG = __name__
logger = setup_logging()



class CustomIceCastClient(miniaudio.IceCastClient):
    def read(self, num_bytes: int) -> bytes:
        """Read a chunk of data from the stream."""
        while len(self._buffer) < num_bytes:
            time.sleep(0.1)
            if self._stop_stream:
                raise ValueError("Steam stoped")
        with self._buffer_lock:
            chunk = self._buffer[:num_bytes]
            self._buffer = self._buffer[num_bytes:]
            return chunk
            

class OpusStreamConverter:
    @staticmethod
    def search_mp3(keywords):
        try:
            encoded_keywords = urllib.parse.quote(keywords)
            search_url = f"https://www.kumeiwp.com/index/search/data?page=1&limit=15&word={encoded_keywords}&scope=all"
            
            logger.bind(tag=TAG).debug(f"Searching {keywords} {search_url}")
            response = requests.get(search_url)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                for item in data['data']:
                    if 'file_id' in item and 'title' in item:
                        file_id = item['file_id']
                        import re
                        title = item['title']
                        if title.startswith('<img src=\"static/images/gs/mp3.gif\"'):
                            logger.bind(tag=TAG).debug(f'Found file_id: {file_id}')
                            mp3_title = keywords
                            title_pattern = r'title="([^"]*)"'
                            title_match = re.search(title_pattern, title)
                            if title_match:
                                mp3_title = title_match.group(1)
                            blacklisted_keywords = ["伴奏", "试听"]
                            if any(blacklisted in mp3_title for blacklisted in blacklisted_keywords):
                                continue
                            # Get the actual MP3 URL from the file page
                            file_url = f"https://www.kumeiwp.com/file/{file_id}.html"
                            file_response = requests.get(file_url)
                            file_response.raise_for_status()
                            
                            # Find the source tag and extract the MP3 URL
                            source_pattern = r'<source src="([^"]*\.mp3)"'
                            sourc_ematch = re.search(source_pattern, file_response.text)
                            if sourc_ematch:
                                mp3_url = sourc_ematch.group(1)
                                logger.bind(tag=TAG).debug(f'Found MP3 URL: {mp3_url}')
                                return mp3_url, mp3_title
            return None, None
            
        except Exception as e:
            logger.bind(tag=TAG).debug(f"Search error: {e}")
            return None, None

    def __init__(self):
        self.buffer = Queue()
        self.is_streaming = True
        self.decoder = None
        self.encoder = None
        self.sample_rate = None
        self.channels = None
        self.frame_size = None
        self.last_frame_time = None
        self.timeout_event = Event()
        self.client = None
        self.stream = None

    def check_timeout(self):
        while not self.timeout_event.is_set():
            if self.last_frame_time and time.time() - self.last_frame_time > 5:
                logger.bind(tag=TAG).debug("No new frames for 5 seconds, closing stream")
                self.buffer.put(None)
                if self.client:
                    self.client.close()
                break
            time.sleep(0.1)
        logger.bind(tag=TAG).debug("check_timeout thread ended")
        #time.sleep(0.1)
        #logger.bind(tag=TAG).debug_all_threads_stack()

    def stream_reader(self, url):
        try:
            logger.bind(tag=TAG).debug(f"stream reader with {url}")
            # Start timeout checker thread
            timeout_thread = Thread(target=self.check_timeout)
            timeout_thread.start()
            self.last_frame_time = time.time()

            self.client = CustomIceCastClient(url)
            logger.bind(tag=TAG).debug("stream client created")
            

            
            self.stream = miniaudio.stream_any(
                source=self.client,
                source_format=miniaudio.FileFormat.MP3,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=16000,
                frames_to_read=960
            )
            logger.bind(tag=TAG).debug("stream started")
            frame_counter = 0
            last_frame_len = 0
            
            for frames in self.stream:
                self.last_frame_time = time.time()
                if not len(frames):
                    logger.bind(tag=TAG).debug("Empty frame detected, stream might have ended")
                    break
                    
                if frame_counter == 0:
                    self.initialize_encoder(frames)
                    logger.bind(tag=TAG).debug(f"Sample Rate: {self.sample_rate}")
                    logger.bind(tag=TAG).debug(f"Channels: {self.channels}")
                    logger.bind(tag=TAG).debug(f"Frame Size: {self.frame_size}")
                
                if not self.is_streaming:
                    logger.bind(tag=TAG).debug("Streaming stopped by user")
                    break
                
                # Check for stream errors or interruptions
                if last_frame_len and len(frames) != last_frame_len:
                    logger.bind(tag=TAG).debug(f"Frame size changed: {last_frame_len} -> {len(frames)}")
                
                last_frame_len = len(frames)
                frame_counter += 1
                self.buffer.put(frames.tobytes())
            
            logger.bind(tag=TAG).debug(f"Stream ended after {frame_counter} frames")
            self.buffer.put(None)
            
        except ConnectionError as e:
            logger.bind(tag=TAG).debug(f"Connection error: {e}")
        except Exception as e:
            logger.bind(tag=TAG).debug(f"Error in stream reader: {e}")
        finally:
            logger.bind(tag=TAG).debug(f"Stream closed")
            self.timeout_event.set()
            try:
                self.buffer.put(None)
                self.client.close()
            except:
                pass

    def initialize_encoder(self, first_frames):
        self.sample_rate = 16000
        self.channels = 1
        self.frame_size = 960
        
        self.encoder = opuslib_next.Encoder(
            self.sample_rate,
            self.channels,
            opuslib_next.APPLICATION_AUDIO
        )

    def convert(self, url, output_file):
        stream_thread = Thread(target=self.stream_reader, args=(url,))
        stream_thread.start()

        try:
            with open(output_file, 'wb') as opus_file:
                while True:
                    pcm_frame = self.buffer.get()
                    if pcm_frame is None:
                        break

                    # Encode PCM to Opus
                    if self.encoder:
                        opus_frame = self.encoder.encode(pcm_frame, self.frame_size)
                        frame_length = len(opus_frame)
                        opus_file.write(struct.pack('<H', frame_length))
                        opus_file.write(opus_frame)

        except Exception as e:
            logger.bind(tag=TAG).debug(f"Error during conversion: {e}")
        finally:
            logger.bind(tag=TAG).debug("Conversion stoping")
            self.is_streaming = False
            stream_thread.join()
    
    def stream_player(self, url, conn, selected_music, stream_thread):
        try:
            opus_packets = []
            started = False
            while True:
                pcm_frame = self.buffer.get()
                if pcm_frame is None:
                    ##music ends
                    if len(opus_packets) > 0:
                        conn.audio_play_queue.put((opus_packets, selected_music + "[end]"))
                    break

                # Encode PCM to Opus
                if self.encoder:
                    opus_frame = self.encoder.encode(pcm_frame, self.frame_size)
                    opus_packets.append(opus_frame)
                    if len(opus_packets) >= 100:
                        if not started:
                            started = True
                            conn.audio_play_queue.put((opus_packets, selected_music + "[start]"))
                        else:
                            conn.audio_play_queue.put((opus_packets, selected_music))
                        opus_packets = []

        except Exception as e:
            logger.bind(tag=TAG).debug(f"Error during streaming: {e}")
        finally:
            logger.bind(tag=TAG).debug("Stream stoping")
            self.is_streaming = False
            stream_thread.join()
            logger.bind(tag=TAG).debug("Stream stoped")

    def play(self, url, conn, selected_music):
        stream_thread = Thread(target=self.stream_reader, args=(url,))
        stream_thread.start()

        playing_thread = Thread(target=self.stream_player, args=(url, conn, selected_music, stream_thread))
        playing_thread.start()




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
        self.music_related_keywords = []

        if "music" in self.config:
            self.music_config = self.config["music"]
            self.music_dir = os.path.abspath(
                self.music_config.get("music_dir", "./music")  # 默认路径修改
            )
            self.music_related_keywords = self.music_config.get("music_commands", [])
            self.music_ext = self.music_config.get("music_ext", (".mp3", ".wav", ".p3"))
            self.refresh_time = self.music_config.get("refresh_time", 60)
        else:
            self.music_dir = os.path.abspath("./music")
            self.music_related_keywords = ["来一首歌", "唱一首歌", "播放音乐", "来点音乐", "背景音乐", "放首歌",
                                           "播放歌曲", "来点背景音乐", "我想听歌", "我要听歌", "放点音乐"]
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

            potential_song = self._extract_song_name(clean_text)
            if potential_song:
                best_match = _find_best_match(potential_song, self.music_files)
                if best_match:
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")
                    await self.play_local_music(conn, specific_file=best_match)
                    return True

        # 检查是否是通用播放音乐命令
        if any(cmd in clean_text for cmd in self.music_related_keywords):
            potential_song = self._extract_song_name(clean_text)
            if potential_song:
                await self.play_remote_music(conn, potential_song)
            else:
                await self.play_local_music(conn)
            return True

        return False

    def _extract_song_name(self, text):
        """从用户输入中提取歌名"""
        for keyword in self.music_related_keywords + ["听", "播放", "放", "唱"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[1].strip()
        return None

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
                if time.time() - self.scan_time > self.refresh_time:
                    # 刷新音乐文件列表
                    self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
                    self.scan_time = time.time()
                    logger.bind(tag=TAG).debug(f"刷新的音乐文件列表: {self.music_files}")

                if not self.music_files:
                    logger.bind(tag=TAG).error("未找到MP3音乐文件")
                    return
                selected_music = random.choice(self.music_files)
                music_path = os.path.join(self.music_dir, selected_music)
                if not os.path.exists(music_path):
                    logger.bind(tag=TAG).error(f"选定的音乐文件不存在: {music_path}")
                    return
            text = f"正在本地播放{selected_music}"
            await send_stt_message(conn, text)
            conn.tts_first_text_index = 0
            conn.tts_last_text_index = 0
            conn.llm_finish_task = True
            if music_path.endswith(".p3"):
                opus_packets, duration = p3.decode_opus_from_file(music_path)
            else:
                opus_packets, duration = conn.tts.wav_to_opus_data(music_path)
            conn.audio_play_queue.put((opus_packets, selected_music, 0))

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")

    async def play_remote_music(self, conn, potential_song):
        try:
            logger.bind(tag=TAG).debug(f"搜索并播放音乐: {potential_song}")
            url, title = OpusStreamConverter.search_mp3(potential_song)
            if url:
                selected_music = title
                text = f"正在搜索播放{selected_music}"
                await send_stt_message(conn, text)
                conn.tts_first_text = selected_music + "[start]"
                conn.tts_last_text = selected_music + "[end]"
                conn.llm_finish_task = True
                converter = OpusStreamConverter()
                logger.bind(tag=TAG).debug(f"Starting playing... {selected_music}")
                converter.play(url, conn, selected_music)
            else:
                logger.bind(tag=TAG).debug("MP3 not found")
        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")