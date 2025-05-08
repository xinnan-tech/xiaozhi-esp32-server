from config.logger import setup_logging
import os
import re
import time
import random
import asyncio
import difflib
import traceback
import requests
from pathlib import Path
from core.utils import p3
from core.handle.sendAudioHandle import send_stt_message
from plugins_func.register import register_function, ToolType, ActionResponse, Action


TAG = __name__
logger = setup_logging()

MUSIC_CACHE = {}

play_music_function_desc = {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "唱歌、听歌、播放音乐的方法。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "歌曲名称，如果用户没有指定具体歌名则为'random', 明确指定的时返回音乐的名字 示例: ```用户:播放两只老虎\n参数：两只老虎``` ```用户:播放音乐 \n参数：random ```"
                            },
                            "artist": {
                                "type": "string",
                                "description": "歌手名称，可选参数。如果指定了歌手名，将使用在线API搜索音乐"
                            },
                            "use_api": {
                                "type": "boolean",
                                "description": "是否使用在线API搜索音乐，默认为false。设置为true时将尝试使用在线API搜索音乐"
                            }
                        },
                        "required": ["song_name"]
                    }
                }
            }


@register_function('play_music', play_music_function_desc, ToolType.SYSTEM_CTL)
def play_music(conn, song_name: str, artist: str = None, use_api: bool = False):
    try:
        # 如果指定了歌手或明确使用API，则使用在线API播放
        if artist or use_api:
            music_intent = f"在线播放音乐 {song_name}"
            if artist:
                music_intent += f" - {artist}"
        else:
            music_intent = f"播放音乐 {song_name}" if song_name != "random" else "随机播放音乐"

        # 检查事件循环状态
        if not conn.loop.is_running():
            logger.bind(tag=TAG).error("事件循环未运行，无法提交任务")
            return ActionResponse(action=Action.RESPONSE, result="系统繁忙", response="请稍后再试")

        # 提交异步任务
        future = asyncio.run_coroutine_threadsafe(
            handle_music_command(conn, music_intent, song_name, artist, use_api),
            conn.loop
        )

        # 非阻塞回调处理
        def handle_done(f):
            try:
                f.result()  # 可在此处理成功逻辑
                logger.bind(tag=TAG).info("播放完成")
            except Exception as e:
                logger.bind(tag=TAG).error(f"播放失败: {e}")

        future.add_done_callback(handle_done)

        return ActionResponse(action=Action.RESPONSE, result="指令已接收", response="正在为您播放音乐")
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")
        return ActionResponse(action=Action.RESPONSE, result=str(e), response="播放音乐时出错了")


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


def get_music_files(music_dir, music_ext):
    music_dir = Path(music_dir)
    music_files = []
    music_file_names = []
    for file in music_dir.rglob("*"):
        # 判断是否是文件
        if file.is_file():
            # 获取文件扩展名
            ext = file.suffix.lower()
            # 判断扩展名是否在列表中
            if ext in music_ext:
                # 添加相对路径
                music_files.append(str(file.relative_to(music_dir)))
                music_file_names.append(os.path.splitext(str(file.relative_to(music_dir)))[0])
    return music_files, music_file_names


def initialize_music_handler(conn):
    global MUSIC_CACHE
    if MUSIC_CACHE == {}:
        if "play_music" in conn.config["plugins"]:
            MUSIC_CACHE["music_config"] = conn.config["plugins"]["play_music"]
            MUSIC_CACHE["music_dir"] = os.path.abspath(
                MUSIC_CACHE["music_config"].get("music_dir", "./music")  # 默认路径修改
            )
            MUSIC_CACHE["music_ext"] = MUSIC_CACHE["music_config"].get("music_ext", (".mp3", ".wav", ".p3"))
            MUSIC_CACHE["refresh_time"] = MUSIC_CACHE["music_config"].get("refresh_time", 60)
            # 在线API配置
            MUSIC_CACHE["api_base_url"] = MUSIC_CACHE["music_config"].get("api_base_url", "http://www.jsrc.top:5566")
            MUSIC_CACHE["temp_dir"] = os.path.abspath(MUSIC_CACHE["music_config"].get("temp_dir", "./temp"))
        else:
            MUSIC_CACHE["music_dir"] = os.path.abspath("./music")
            MUSIC_CACHE["music_ext"] = (".mp3", ".wav", ".p3")
            MUSIC_CACHE["refresh_time"] = 60
            MUSIC_CACHE["api_base_url"] = "http://www.jsrc.top:5566"
            MUSIC_CACHE["temp_dir"] = os.path.abspath("./temp")
            
        # 确保临时目录存在
        os.makedirs(MUSIC_CACHE["temp_dir"], exist_ok=True)
            
        # 获取音乐文件列表
        MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = get_music_files(MUSIC_CACHE["music_dir"],
                                                                                      MUSIC_CACHE["music_ext"])
        MUSIC_CACHE["scan_time"] = time.time()
    return MUSIC_CACHE


async def handle_music_command(conn, text, song_name=None, artist=None, use_api=False):
    initialize_music_handler(conn)
    global MUSIC_CACHE

    """处理音乐播放指令"""
    clean_text = re.sub(r'[^\w\s]', '', text).strip()
    logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

    # 如果指定了歌手或明确使用API，则使用在线API播放
    if artist or use_api:
        logger.bind(tag=TAG).info(f"使用在线API播放音乐: {song_name} - {artist if artist else '未指定歌手'}")
        await play_api_music(conn, song_name, artist)
        return True

    # 尝试匹配具体歌名
    if os.path.exists(MUSIC_CACHE["music_dir"]):
        if time.time() - MUSIC_CACHE["scan_time"] > MUSIC_CACHE["refresh_time"]:
            # 刷新音乐文件列表
            MUSIC_CACHE["music_files"], MUSIC_CACHE["music_file_names"] = get_music_files(MUSIC_CACHE["music_dir"],
                                                                                          MUSIC_CACHE["music_ext"])
            MUSIC_CACHE["scan_time"] = time.time()

        potential_song = _extract_song_name(clean_text)
        if potential_song:
            best_match = _find_best_match(potential_song, MUSIC_CACHE["music_files"])
            if best_match:
                logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")
                await play_local_music(conn, specific_file=best_match)
                return True
                
    # 如果本地没找到匹配的歌曲，且song_name不是random，尝试使用在线API
    if song_name != "random" and song_name != "":
        logger.bind(tag=TAG).info(f"本地未找到匹配歌曲，尝试使用在线API: {song_name}")
        success = await play_api_music(conn, song_name, artist)
        if success:
            return True
            
    # 如果在线API也失败或song_name为random，则随机播放本地音乐
    await play_local_music(conn)
    return True


async def play_local_music(conn, specific_file=None):
    global MUSIC_CACHE
    """播放本地音乐文件"""
    try:
        if not os.path.exists(MUSIC_CACHE["music_dir"]):
            logger.bind(tag=TAG).error(f"音乐目录不存在: " + MUSIC_CACHE["music_dir"])
            return False

        # 确保路径正确性
        if specific_file:
            selected_music = specific_file
            music_path = os.path.join(MUSIC_CACHE["music_dir"], specific_file)
        else:
            if not MUSIC_CACHE["music_files"]:
                logger.bind(tag=TAG).error("未找到MP3音乐文件")
                return False
            selected_music = random.choice(MUSIC_CACHE["music_files"])
            music_path = os.path.join(MUSIC_CACHE["music_dir"], selected_music)

        if not os.path.exists(music_path):
            logger.bind(tag=TAG).error(f"选定的音乐文件不存在: {music_path}")
            return False
            
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
        return True

    except Exception as e:
        logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
        logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
        return False


async def play_api_music(conn, song_name, artist=None):
    """通过在线API播放音乐"""
    global MUSIC_CACHE
    
    try:
        # 1. 获取音乐信息
        music_info = await get_music_info(song_name, artist)
        if not music_info:
            await send_stt_message(conn, f"抱歉，没有找到歌曲 {song_name}")
            return False
            
        # 2. 下载音频文件
        audio_url = music_info.get("audioUrl")
        if not audio_url:
            await send_stt_message(conn, "获取音乐链接失败")
            return False
            
        # 生成随机文件名
        random_name = f"music_{int(time.time())}_{random.randint(1000, 9999)}.mp3"
        audio_path = os.path.join(MUSIC_CACHE["temp_dir"], random_name)
        
        # 下载音频文件
        success = await download_file(audio_url, audio_path)
        if not success:
            await send_stt_message(conn, "下载音乐失败")
            return False
        
        # 3. 播放音乐（使用与本地音乐相同的播放逻辑）
        display_name = f"{song_name}"
        if artist:
            display_name += f" - {artist}"
            
        # 发送播放消息
        await send_stt_message(conn, f"正在播放 {display_name}")
        
        # 重置TTS状态
        conn.tts_first_text_index = 0
        conn.tts_last_text_index = 0
        conn.llm_finish_task = True
        
        # 解码音频文件
        if audio_path.endswith(".p3"):
            opus_packets, duration = p3.decode_opus_from_file(audio_path)
        else:
            opus_packets, duration = conn.tts.audio_to_opus_data(audio_path)
        
        # 将音频帧放入播放队列
        conn.audio_play_queue.put((opus_packets, display_name, 0))
        
        # 播放完成后删除临时文件
        try:
            os.remove(audio_path)
        except:
            pass
            
        return True
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"API音乐播放出错: {str(e)}")
        logger.bind(tag=TAG).error(traceback.format_exc())
        await send_stt_message(conn, f"播放音乐时出错: {str(e)}")
        return False


async def get_music_info(song_name, artist=None):
    """获取音乐信息（音频URL）"""
    global MUSIC_CACHE
    
    try:
        url_builder = f"{MUSIC_CACHE['api_base_url']}/stream_pcm?song={requests.utils.quote(song_name)}"
        if artist:
            url_builder += f"&artist={requests.utils.quote(artist)}"
            
        response = requests.get(url_builder)
        if response.status_code != 200:
            logger.bind(tag=TAG).error(f"获取音乐信息失败，响应码: {response.status_code}")
            return None
            
        response_data = response.json()
        result = {}
        
        # 检查API响应格式，支持两种可能的字段名
        audio_path = response_data.get("audioPath")
        audio_url = response_data.get("audio_url")
        
        # 优先使用直接URL，否则构建URL
        if audio_url and not audio_url.startswith("http"):
            audio_url = f"{MUSIC_CACHE['api_base_url']}{audio_url}"
        elif audio_path:
            audio_url = f"{MUSIC_CACHE['api_base_url']}/get_file?path={requests.utils.quote(audio_path)}&name={requests.utils.quote(song_name + '.mp3')}"
        else:
            logger.bind(tag=TAG).error("API响应中缺少音频URL信息")
            return None
            
        result["audioUrl"] = audio_url
        return result
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"获取音乐信息时发生错误: {str(e)}")
        return None


async def download_file(file_url, output_path):
    """下载文件到指定路径"""
    try:
        response = requests.get(file_url, stream=True)
        if response.status_code != 200:
            logger.bind(tag=TAG).error(f"下载文件失败，响应码: {response.status_code}")
            return False
            
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        logger.bind(tag=TAG).error(f"下载文件时发生错误: {str(e)}")
        return False