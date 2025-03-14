# 导入所需的模块
from config.logger import setup_logging  # 导入日志设置模块
import os  # 导入操作系统模块，用于处理文件和目录路径
import random  # 导入随机模块，用于随机选择音乐文件
import difflib  # 导入差异比较模块，用于字符串匹配
import re  # 导入正则表达式模块，用于文本处理
import traceback  # 导入异常处理模块，用于捕获和记录异常信息
from pathlib import Path  # 导入路径处理模块，用于处理文件路径
import time  # 导入时间模块，用于处理时间相关的操作
from core.handle.sendAudioHandle import send_stt_message  # 导入发送音频消息的模块
from core.utils import p3  # 导入自定义的p3模块，用于处理.p3格式的音频文件

# 定义当前模块的标签，通常用于日志记录
TAG = __name__

# 设置日志记录器
logger = setup_logging()

def _extract_song_name(text):
    """从用户输入中提取歌名"""
    # 遍历关键词列表，尝试从用户输入中提取歌名
    for keyword in ["听", "播放", "放", "唱"]:
        if keyword in text:
            # 如果找到关键词，将文本分割并提取歌名部分
            parts = text.split(keyword)
            if len(parts) > 1:
                return parts[1].strip()  # 返回提取的歌名并去除前后空格
    return None  # 如果没有找到关键词，返回None

def _find_best_match(potential_song, music_files):
    """查找最匹配的歌曲"""
    best_match = None  # 初始化最佳匹配的歌曲文件
    highest_ratio = 0  # 初始化最高匹配度

    # 遍历音乐文件列表，查找与潜在歌名最匹配的文件
    for music_file in music_files:
        song_name = os.path.splitext(music_file)[0]  # 去除文件扩展名，获取歌曲名
        ratio = difflib.SequenceMatcher(None, potential_song, song_name).ratio()  # 计算匹配度
        if ratio > highest_ratio and ratio > 0.4:  # 如果匹配度高于当前最高值且大于0.4
            highest_ratio = ratio  # 更新最高匹配度
            best_match = music_file  # 更新最佳匹配的歌曲文件
    return best_match  # 返回最佳匹配的歌曲文件

class MusicManager:
    """音乐文件管理类，用于管理音乐文件的获取和扫描"""
    def __init__(self, music_dir, music_ext):
        """初始化音乐管理器"""
        self.music_dir = Path(music_dir)  # 设置音乐目录路径
        self.music_ext = music_ext  # 设置音乐文件的扩展名列表

    def get_music_files(self):
        """获取音乐文件列表"""
        music_files = []  # 初始化音乐文件列表
        for file in self.music_dir.rglob("*"):  # 遍历音乐目录及其子目录中的所有文件
            if file.is_file():  # 判断是否是文件
                ext = file.suffix.lower()  # 获取文件扩展名并转换为小写
                if ext in self.music_ext:  # 如果扩展名在允许的扩展名列表中
                    music_files.append(str(file.relative_to(self.music_dir)))  # 添加相对路径到音乐文件列表
        return music_files  # 返回音乐文件列表

class MusicHandler:
    """音乐处理类，用于处理音乐播放相关的指令"""
    def __init__(self, config):
        """初始化音乐处理器"""
        self.config = config  # 设置配置信息
        self.music_related_keywords = []  # 初始化音乐相关关键词列表

        # 从配置中获取音乐相关的设置
        if "music" in self.config:
            self.music_config = self.config["music"]
            self.music_dir = os.path.abspath(
                self.music_config.get("music_dir", "./music")  # 获取音乐目录路径，默认为"./music"
            )
            self.music_related_keywords = self.music_config.get("music_commands", [])  # 获取音乐相关关键词
            self.music_ext = self.music_config.get("music_ext", (".mp3", ".wav", ".p3"))  # 获取音乐文件扩展名
            self.refresh_time = self.music_config.get("refresh_time", 60)  # 获取音乐文件列表刷新时间，默认为60秒
        else:
            # 如果配置中没有音乐相关设置，使用默认值
            self.music_dir = os.path.abspath("./music")
            self.music_related_keywords = ["来一首歌", "唱一首歌", "播放音乐", "来点音乐", "背景音乐", "放首歌",
                                           "播放歌曲", "来点背景音乐", "我想听歌", "我要听歌", "放点音乐"]
            self.music_ext = (".mp3", ".wav", ".p3")
            self.refresh_time = 60

        # 获取音乐文件列表
        self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
        self.scan_time = time.time()  # 记录当前时间，用于后续刷新音乐文件列表
        logger.bind(tag=TAG).debug(f"找到的音乐文件: {self.music_files}")  # 记录找到的音乐文件

    async def handle_music_command(self, conn, text):
        """处理音乐播放指令"""
        clean_text = re.sub(r'[^\w\s]', '', text).strip()  # 清理文本，去除标点符号
        logger.bind(tag=TAG).debug(f"检查是否是音乐命令: {clean_text}")  # 记录检查的音乐命令

        # 尝试匹配具体歌名
        if os.path.exists(self.music_dir):  # 检查音乐目录是否存在
            if time.time() - self.scan_time > self.refresh_time:  # 如果超过刷新时间，刷新音乐文件列表
                self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
                self.scan_time = time.time()  # 更新扫描时间
                logger.bind(tag=TAG).debug(f"刷新的音乐文件: {self.music_files}")  # 记录刷新的音乐文件

            potential_song = _extract_song_name(clean_text)  # 从用户输入中提取歌名
            if potential_song:  # 如果提取到歌名
                best_match = _find_best_match(potential_song, self.music_files)  # 查找最匹配的歌曲
                if best_match:  # 如果找到匹配的歌曲
                    logger.bind(tag=TAG).info(f"找到最匹配的歌曲: {best_match}")  # 记录找到的歌曲
                    await self.play_local_music(conn, specific_file=best_match)  # 播放匹配的歌曲
                    return True  # 返回True表示成功处理音乐命令

        # 检查是否是通用播放音乐命令
        if any(cmd in clean_text for cmd in self.music_related_keywords):  # 如果用户输入包含音乐相关关键词
            await self.play_local_music(conn)  # 播放随机音乐
            return True  # 返回True表示成功处理音乐命令

        return False  # 如果没有处理音乐命令，返回False

    async def play_local_music(self, conn, specific_file=None):
        """播放本地音乐文件"""
        try:
            if not os.path.exists(self.music_dir):  # 检查音乐目录是否存在
                logger.bind(tag=TAG).error(f"音乐目录不存在: {self.music_dir}")  # 记录错误信息
                return

            # 确保路径正确性
            if specific_file:  # 如果指定了具体的音乐文件
                music_path = os.path.join(self.music_dir, specific_file)  # 拼接音乐文件路径
                if not os.path.exists(music_path):  # 检查音乐文件是否存在
                    logger.bind(tag=TAG).error(f"指定的音乐文件不存在: {music_path}")  # 记录错误信息
                    return
                selected_music = specific_file  # 设置选定的音乐文件
            else:
                if time.time() - self.scan_time > self.refresh_time:  # 如果超过刷新时间，刷新音乐文件列表
                    self.music_files = MusicManager(self.music_dir, self.music_ext).get_music_files()
                    self.scan_time = time.time()  # 更新扫描时间
                    logger.bind(tag=TAG).debug(f"刷新的音乐文件列表: {self.music_files}")  # 记录刷新的音乐文件列表

                if not self.music_files:  # 如果没有找到音乐文件
                    logger.bind(tag=TAG).error("未找到MP3音乐文件")  # 记录错误信息
                    return
                selected_music = random.choice(self.music_files)  # 随机选择一个音乐文件
                music_path = os.path.join(self.music_dir, selected_music)  # 拼接音乐文件路径
                if not os.path.exists(music_path):  # 检查音乐文件是否存在
                    logger.bind(tag=TAG).error(f"选定的音乐文件不存在: {music_path}")  # 记录错误信息
                    return
            text = f"正在播放{selected_music}"  # 设置播放提示信息
            await send_stt_message(conn, text)  # 发送播放提示信息
            conn.tts_first_text_index = 0  # 重置TTS文本索引
            conn.tts_last_text_index = 0  # 重置TTS文本索引
            conn.llm_finish_task = True  # 标记任务完成
            if music_path.endswith(".p3"):  # 如果音乐文件是.p3格式
                opus_packets, duration = p3.decode_opus_from_file(music_path)  # 解码.p3文件
            else:
                opus_packets, duration = conn.tts.wav_to_opus_data(music_path)  # 将.wav文件转换为opus数据
            conn.audio_play_queue.put((opus_packets, selected_music, 0))  # 将音频数据放入播放队列

        except Exception as e:
            logger.bind(tag=TAG).error(f"播放音乐失败: {str(e)}")  # 记录播放失败的错误信息
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")  # 记录详细的错误信息