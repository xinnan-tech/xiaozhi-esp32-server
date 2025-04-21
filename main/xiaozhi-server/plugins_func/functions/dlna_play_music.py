from config.logger import setup_logging 
import re
import time
import random
import asyncio
import difflib
import traceback
  
from plugins_func.register import register_function,ToolType, ActionResponse, Action
from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.client import UpnpDevice
from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice

TAG = __name__
logger = setup_logging()

DLNA_MUSIC_CACHE = {}
FUNCTION_NAME = 'dlna_play_music'

dlna_play_music_function_desc = {
                "type": "function",
                "function": {
                    "name": FUNCTION_NAME,
                    "description": "唱歌、听歌、播放音乐的方法。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "歌曲名称，如果用户没有指定具体歌名则为'random', 明确指定的时返回音乐的名字 示例: ```用户:播放两只老虎\n参数：两只老虎``` ```用户:播放音乐 \n参数：random ```"
                            }
                        },
                        "required": ["song_name"]
                    }
                }
            }


@register_function(FUNCTION_NAME, dlna_play_music_function_desc, ToolType.SYSTEM_CTL)
def dlna_play_music(conn, song_name: str):
    try:
        music_intent = f"播放音乐 {song_name}" if song_name != "random" else "随机播放音乐"

        # 执行音乐播放命令
        future = asyncio.run_coroutine_threadsafe(
            play_dlna_music(conn, music_intent),
            conn.loop
        )

        response = future.result()
        return ActionResponse(action=Action.RESPONSE, result="指令已接收", response=response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")

async def _discover_dlna_device(factory:UpnpFactory ,upnpDevice: UpnpDevice, name: str = None) -> UpnpDevice:
    """发现 DLNA 设备"""
    discoveries = await upnpDevice.async_search(source=("0.0.0.0", 0),timeout=1)
    
    if discoveries:
        for item in list(discoveries):
            location = item["location"]
            device = await factory.async_create_device(description_url=location)
            if name == None or difflib.SequenceMatcher(None, name, device.friendly_name).ratio() > 0.5:
                logger.bind(tag=TAG).info(f"播放设备: {device.friendly_name}")
                return upnpDevice(device, None)

    return

def _extract_song_name(text):
    """从用户输入中提取歌名"""
    for keyword in ["播放音乐"]:
        if keyword in text:
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip()
    return None


def _find_best_match(potential_song, musics):
    """查找最匹配的歌曲"""
    best_match = None
    highest_ratio = 0

    for item in musics:
        ratio = difflib.SequenceMatcher(None, potential_song, item[0]).ratio()
        if ratio > highest_ratio and ratio > 0.4:
            highest_ratio = ratio
            best_match = item
    return best_match

async def _get_musics() -> list:
    global DLNA_MUSIC_CACHE
    """获取音乐文件列表"""
    requester = AiohttpRequester()
    factory = UpnpFactory(requester, non_strict=True)
    dms_device = await _discover_dlna_device(factory,DmsDevice, DLNA_MUSIC_CACHE["dms_name"])
    DLNA_MUSIC_CACHE["dlna_dms_device"] = dms_device
    DLNA_MUSIC_CACHE["dlna_dmr_device"] = await _discover_dlna_device(factory,DmrDevice,DLNA_MUSIC_CACHE["dmr_name"])

    musics = []
    items = await dms_device.async_browse_direct_children( object_id="1$4")
    for item in items[0]:
        if item.res:
            musics.append([item.title, item.res[0].uri]) 

    return musics

async def initialize_music_handler(conn):
    global DLNA_MUSIC_CACHE
    if DLNA_MUSIC_CACHE == {}:
        if FUNCTION_NAME in conn.config["plugins"]:
            music_config = conn.config["plugins"][FUNCTION_NAME]
            DLNA_MUSIC_CACHE["music_config"] = music_config
            DLNA_MUSIC_CACHE["dms_name"] = music_config.get("dms_name")
            DLNA_MUSIC_CACHE["dmr_name"] = music_config.get("dmr_name")
            DLNA_MUSIC_CACHE["refresh_time"] = music_config.get("refresh_time", 60)
        else:
            DLNA_MUSIC_CACHE["refresh_time"] = 60 

        # 获取音乐文件列表
        DLNA_MUSIC_CACHE["musics"] = await _get_musics()
        DLNA_MUSIC_CACHE["scan_time"] = time.time()
    return DLNA_MUSIC_CACHE


async def play_dlna_music(conn, text):
    DLNA_MUSIC_CACHE = await initialize_music_handler(conn)

    """处理音乐播放指令"""
    clean_text = re.sub(r'[^\w\s]', '', text).strip()
    logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")

    music = None
    # 尝试匹配具体歌名
    if DLNA_MUSIC_CACHE["dlna_dms_device"]:
        if time.time() - DLNA_MUSIC_CACHE["scan_time"] > DLNA_MUSIC_CACHE["refresh_time"]:
            # 刷新音乐文件列表
            DLNA_MUSIC_CACHE["musics"] = await _get_musics()
            DLNA_MUSIC_CACHE["scan_time"] = time.time()

        potential_song = _extract_song_name(clean_text)
        if potential_song:
            music = _find_best_match(potential_song, DLNA_MUSIC_CACHE["musics"])

    """播放 DLNA 音乐文件"""
    try:
        if not DLNA_MUSIC_CACHE["dlna_dms_device"]:
            logger.bind(tag=TAG).error(f"DLNA DMS 不存在")
            return
        
        dmr_device = DLNA_MUSIC_CACHE["dlna_dmr_device"]
        if not dmr_device:
            logger.bind(tag=TAG).error(f"DLNA DMR 不存在")
            return

        # 确保路径正确性
        if music:
            logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {music}")
            selected_music = music
        else:
            if not DLNA_MUSIC_CACHE["musics"]:
                logger.bind(tag=TAG).error("未找到音乐文件")
                return
            selected_music = random.choice(DLNA_MUSIC_CACHE["musics"])
             
        # Stop current playing media
        if dmr_device.can_stop:
            await dmr_device.async_stop()
        # Queue media
        await dmr_device.async_set_transport_uri(
                media_title=selected_music[0],
                media_url=selected_music[1],
            )
        # Play it
        await dmr_device.async_wait_for_can_play()
        await dmr_device.async_play()
        return f"正在播放{selected_music[0]}"

    except Exception as e:
        logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")
        logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
