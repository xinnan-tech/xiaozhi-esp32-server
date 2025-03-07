import os
import uuid
import requests
import aiohttp
import aiofiles
import time
import random
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging
from core.utils.util import get_project_dir

logger = setup_logging()
TAG = "CosyVoice"

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        # Get configuration parameters
        self.api_url = config.get("api_url", "http://127.0.0.1:9881/tts")
        self.mode = config.get("mode", "预训练音色")  # 预训练音色, 3s极速复刻, 跨语种复刻, 自然语言控制
        self.speaker = config.get("speaker", None)
        self.response_format = config.get("response_format", "wav")
        self.timeout = config.get("timeout", 120)  # Increased timeout for larger audio files
        self.max_retries = config.get("max_retries", 3)  # Maximum number of retries
        self.retry_delay = config.get("retry_delay", 1)  # Delay between retries in seconds
        
        # Optional parameters
        self.prompt_audio = config.get("prompt_audio", None)
        self.prompt_text = config.get("prompt_text", None)
        self.instruct_text = config.get("instruct_text", None)
        self.seed = config.get("seed", 0)
        self.speed = config.get("speed", 1.0)
        self.stream = config.get("stream", False)
        
        # 获取项目根目录
        self.project_dir = get_project_dir()
        
        logger.bind(tag=TAG).info(f"CosyVoice V2 TTS initialized with API URL: {self.api_url}")
        logger.bind(tag=TAG).info(f"Mode: {self.mode}, Speaker: {self.speaker}")
        
        # Validate configuration
        if self.mode == "预训练音色" and not self.speaker:
            logger.bind(tag=TAG).warning("预训练音色模式需要指定speaker参数")
        
        if self.mode == "3s极速复刻" and (not self.prompt_audio or not self.prompt_text):
            logger.bind(tag=TAG).warning("3s极速复刻模式需要指定prompt_audio和prompt_text参数")
        
        if self.mode == "跨语种复刻" and not self.prompt_audio:
            logger.bind(tag=TAG).warning("跨语种复刻模式需要指定prompt_audio参数")
        
        if self.mode == "自然语言控制" and (not self.speaker or not self.instruct_text):
            logger.bind(tag=TAG).warning("自然语言控制模式需要指定speaker和instruct_text参数")

    def generate_filename(self, extension=".wav"):
        """Generate a unique filename for the TTS output"""
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def get_absolute_path(self, file_path):
        """将相对路径转换为绝对路径"""
        if not file_path:
            return None
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(file_path):
            return file_path
            
        # 否则，将其转换为相对于项目根目录的绝对路径
        return os.path.join(self.project_dir, file_path)

    async def text_to_speak(self, text, output_file):
        """
        将文本转换为语音
        :param text: 文本
        :param output_file: 输出文件路径
        :return: 语音文件路径
        """
        prompt_audio_file = None
        retry_count = 0
        last_error = None
        temp_output_file = f"{output_file}.temp"
        
        while retry_count < self.max_retries:
            try:
                # 准备通用表单数据
                data = aiohttp.FormData()
                data.add_field('text', text)
                data.add_field('mode', self.mode)
                
                # 根据模式添加不同的参数
                if self.mode == "预训练音色":
                    if self.speaker:
                        data.add_field('speaker', self.speaker)
                
                elif self.mode == "3s极速复刻":
                    if self.prompt_text:
                        data.add_field('prompt_text', self.prompt_text)
                    
                    # 添加音频文件
                    prompt_audio_path = self.get_absolute_path(self.prompt_audio)
                    if prompt_audio_path and os.path.exists(prompt_audio_path):
                        logger.bind(tag=TAG).info(f"使用音频文件: {prompt_audio_path}")
                        try:
                            prompt_audio_file = open(prompt_audio_path, 'rb')
                            data.add_field('prompt_audio', 
                                          prompt_audio_file,
                                          filename=os.path.basename(prompt_audio_path),
                                          content_type='audio/mpeg' if prompt_audio_path.lower().endswith('.mp3') else 'audio/wav')
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"打开音频文件失败: {prompt_audio_path}, 错误: {str(e)}")
                            raise FileNotFoundError(f"打开音频文件失败: {prompt_audio_path}, 错误: {str(e)}")
                    else:
                        logger.bind(tag=TAG).error(f"提示音频文件不存在: {prompt_audio_path}")
                        raise FileNotFoundError(f"提示音频文件不存在: {prompt_audio_path}")
                
                elif self.mode == "跨语种复刻":
                    # 添加音频文件
                    prompt_audio_path = self.get_absolute_path(self.prompt_audio)
                    if prompt_audio_path and os.path.exists(prompt_audio_path):
                        logger.bind(tag=TAG).info(f"使用音频文件: {prompt_audio_path}")
                        try:
                            prompt_audio_file = open(prompt_audio_path, 'rb')
                            data.add_field('prompt_audio', 
                                          prompt_audio_file,
                                          filename=os.path.basename(prompt_audio_path),
                                          content_type='audio/mpeg' if prompt_audio_path.lower().endswith('.mp3') else 'audio/wav')
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"打开音频文件失败: {prompt_audio_path}, 错误: {str(e)}")
                            raise FileNotFoundError(f"打开音频文件失败: {prompt_audio_path}, 错误: {str(e)}")
                    else:
                        logger.bind(tag=TAG).error(f"提示音频文件不存在: {prompt_audio_path}")
                        raise FileNotFoundError(f"提示音频文件不存在: {prompt_audio_path}")
                
                elif self.mode == "自然语言控制":
                    if self.speaker:
                        data.add_field('speaker', self.speaker)
                    if self.instruct_text:
                        data.add_field('instruct_text', self.instruct_text)
                
                # 添加通用参数
                data.add_field('seed', str(self.seed))
                data.add_field('speed', str(self.speed))
                data.add_field('stream', str(self.stream).lower())
                
                # 发送请求
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                # 强制关闭连接，避免连接池问题
                connector = aiohttp.TCPConnector(force_close=True, ssl=False)
                
                # 使用临时文件来避免文件损坏
                async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=True) as session:
                    try:
                        # 使用chunked传输编码，不设置Content-Length
                        headers = {
                            'Accept': 'audio/wav, audio/mpeg, audio/*'
                        }
                        
                        async with session.post(
                            self.api_url,
                            data=data,
                            headers=headers,
                            allow_redirects=False,
                            chunked=True  # 使用分块传输编码
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.bind(tag=TAG).error(f"CosyVoice TTS API 请求失败: {response.status}, {error_text}")
                                raise Exception(f"CosyVoice TTS API 请求失败: {response.status}, {error_text}")
                            
                            # 检查响应头中是否有错误信息
                            content_type = response.headers.get('Content-Type', '')
                            if 'application/json' in content_type:
                                error_json = await response.json()
                                if 'error' in error_json:
                                    raise Exception(f"API返回错误: {error_json['error']}")
                            
                            # 使用流式读取响应内容到临时文件
                            async with aiofiles.open(temp_output_file, 'wb') as f:
                                # 分块读取响应内容
                                chunk_size = 8192  # 8KB 块大小
                                total_bytes = 0
                                
                                try:
                                    async for chunk in response.content.iter_chunked(chunk_size):
                                        if chunk:
                                            await f.write(chunk)
                                            total_bytes += len(chunk)
                                except aiohttp.ClientPayloadError as e:
                                    # 处理内容长度不匹配的情况
                                    logger.bind(tag=TAG).warning(f"内容传输中断: {str(e)}，已接收 {total_bytes} 字节")
                                    # 如果已经接收了一些数据，我们可以继续处理
                                    if total_bytes > 0:
                                        logger.bind(tag=TAG).info(f"尽管传输中断，但已接收 {total_bytes} 字节的数据，将继续处理")
                                    else:
                                        raise
                            
                            # 验证文件大小
                            if total_bytes == 0:
                                raise Exception("接收到的音频数据为空")
                            
                            # 检查临时文件是否存在且非空
                            if not os.path.exists(temp_output_file) or os.path.getsize(temp_output_file) == 0:
                                raise Exception("生成的临时音频文件为空")
                            
                            # 将临时文件重命名为最终文件
                            try:
                                # 如果目标文件已存在，先删除
                                if os.path.exists(output_file):
                                    os.remove(output_file)
                                os.rename(temp_output_file, output_file)
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"重命名文件失败: {str(e)}")
                                # 尝试复制文件内容
                                try:
                                    with open(temp_output_file, 'rb') as src, open(output_file, 'wb') as dst:
                                        dst.write(src.read())
                                    # 删除临时文件
                                    os.remove(temp_output_file)
                                except Exception as copy_error:
                                    logger.bind(tag=TAG).error(f"复制文件内容失败: {str(copy_error)}")
                                    raise Exception(f"无法创建输出文件: {str(e)}, 复制失败: {str(copy_error)}")
                            
                            logger.bind(tag=TAG).info(f"TTS 生成成功，保存到: {output_file}，大小: {total_bytes} 字节")
                            return output_file
                    except aiohttp.ClientError as e:
                        logger.bind(tag=TAG).error(f"网络请求错误: {str(e)}")
                        last_error = Exception(f"网络请求错误: {str(e)}")
                        # 如果是连接问题，重试
                        retry_count += 1
                        if retry_count < self.max_retries:
                            logger.bind(tag=TAG).warning(f"重试 ({retry_count}/{self.max_retries})...")
                            time.sleep(self.retry_delay)
                            continue
                        raise last_error
                        
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    logger.bind(tag=TAG).warning(f"TTS 生成失败: {str(e)}，重试 ({retry_count}/{self.max_retries})...")
                    # 添加随机延迟，避免同时重试
                    time.sleep(self.retry_delay + random.uniform(0, 1))
                    continue
                logger.bind(tag=TAG).error(f"CosyVoice TTS 生成失败: {str(e)}")
                raise e
            finally:
                # 确保关闭文件句柄
                if prompt_audio_file:
                    prompt_audio_file.close()
                
                # 清理临时文件
                if os.path.exists(temp_output_file):
                    try:
                        os.remove(temp_output_file)
                    except Exception as e:
                        logger.bind(tag=TAG).warning(f"清理临时文件失败: {str(e)}")
        
        # 如果所有重试都失败
        if last_error:
            raise last_error
        return None 