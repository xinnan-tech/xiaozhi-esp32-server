import asyncio
import json
import time
import aiohttp
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class VoiceprintProvider:
    """声纹识别服务提供者"""
    
    def __init__(self, config: dict):
        self.original_url = config.get("url", "")
        self.speakers = config.get("speakers", [])
        self.speaker_map = self._parse_speakers()
        
        # 解析API地址和密钥
        self.api_url = None
        self.api_key = None
        self.speaker_ids = []
        
        if not self.original_url:
            logger.bind(tag=TAG).warning("声纹识别URL未配置，声纹识别将被禁用")
            self.enabled = False
        else:
            # 解析URL和key
            parsed_url = urlparse(self.original_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # 从查询参数中提取key
            query_params = parse_qs(parsed_url.query)
            self.api_key = query_params.get('key', [''])[0]
            
            if not self.api_key:
                logger.bind(tag=TAG).error("URL中未找到key参数，声纹识别将被禁用")
                self.enabled = False
            else:
                # 构造identify接口地址
                self.api_url = f"{base_url}/voiceprint/identify"
                
                # 提取speaker_ids
                for speaker_str in self.speakers:
                    try:
                        parts = speaker_str.split(",", 2)
                        if len(parts) >= 1:
                            speaker_id = parts[0].strip()
                            self.speaker_ids.append(speaker_id)
                    except Exception:
                        continue
                
                # 检查是否有有效的说话人配置
                if not self.speaker_ids:
                    logger.bind(tag=TAG).warning("未配置有效的说话人，声纹识别将被禁用")
                    self.enabled = False
                else:
                    self.enabled = True
                    logger.bind(tag=TAG).info(f"声纹识别已配置: API={self.api_url}, 说话人={len(self.speaker_ids)}个")
    
    def _parse_speakers(self) -> Dict[str, Dict[str, str]]:
        """解析说话人配置"""
        speaker_map = {}
        for speaker_str in self.speakers:
            try:
                parts = speaker_str.split(",", 2)
                if len(parts) >= 3:
                    speaker_id, name, description = parts[0].strip(), parts[1].strip(), parts[2].strip()
                    speaker_map[speaker_id] = {
                        "name": name,
                        "description": description
                    }
            except Exception as e:
                logger.bind(tag=TAG).warning(f"解析说话人配置失败: {speaker_str}, 错误: {e}")
        return speaker_map
    
    async def identify_speaker(self, audio_data: bytes, session_id: str) -> Optional[str]:
        """识别说话人"""
        if not self.enabled or not self.api_url or not self.api_key:
            logger.bind(tag=TAG).debug("声纹识别功能已禁用或未配置，跳过识别")
            return None
            
        try:
            api_start_time = time.monotonic()
            
            # 准备请求头
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            # 准备multipart/form-data数据
            data = aiohttp.FormData()
            data.add_field('speaker_ids', ','.join(self.speaker_ids))
            data.add_field('file', audio_data, filename='audio.wav', content_type='audio/wav')
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            # 网络请求
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, headers=headers, data=data) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        speaker_id = result.get("speaker_id")
                        score = result.get("score", 0)
                        total_elapsed_time = time.monotonic() - api_start_time
                        
                        logger.bind(tag=TAG).info(f"声纹识别耗时: {total_elapsed_time:.3f}s")
                        
                        # 置信度检查
                        if score < 0.5:
                            logger.bind(tag=TAG).warning(f"声纹识别置信度较低: {score:.3f}")
                        
                        if speaker_id and speaker_id in self.speaker_map:
                            result_name = self.speaker_map[speaker_id]["name"]
                            return result_name
                        else:
                            logger.bind(tag=TAG).warning(f"未识别的说话人ID: {speaker_id}")
                            return "未知说话人"
                    else:
                        logger.bind(tag=TAG).error(f"声纹识别API错误: HTTP {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(f"声纹识别超时: {elapsed:.3f}s")
            return None
        except Exception as e:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(f"声纹识别失败: {e}")
            return None