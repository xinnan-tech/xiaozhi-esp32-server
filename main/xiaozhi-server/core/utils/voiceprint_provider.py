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
    """Voiceprint recognition service provider"""
    
    def __init__(self, config: dict):
        self.original_url = config.get("url", "")
        self.speakers = config.get("speakers", [])
        self.speaker_map = self._parse_speakers()
        
        # Parse API address and key
        self.api_url = None
        self.api_key = None
        self.speaker_ids = []
        
        if not self.original_url:
            logger.bind(tag=TAG).warning("Voiceprint recognition URL not configured, voiceprint recognition will be disabled")
            self.enabled = False
        else:
            # Parse URL and key
            parsed_url = urlparse(self.original_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Extract key from query parameters
            query_params = parse_qs(parsed_url.query)
            self.api_key = query_params.get('key', [''])[0]
            
            if not self.api_key:
                logger.bind(tag=TAG).error("Key parameter not found in URL, voiceprint recognition will be disabled")
                self.enabled = False
            else:
                # Construct identify interface address
                self.api_url = f"{base_url}/voiceprint/identify"
                
                # Extract speaker_ids
                for speaker_str in self.speakers:
                    try:
                        parts = speaker_str.split(",", 2)
                        if len(parts) >= 1:
                            speaker_id = parts[0].strip()
                            self.speaker_ids.append(speaker_id)
                    except Exception:
                        continue
                
                # Check if there are valid speaker configurations
                if not self.speaker_ids:
                    logger.bind(tag=TAG).warning("No valid speakers configured, voiceprint recognition will be disabled")
                    self.enabled = False
                else:
                    self.enabled = True
                    logger.bind(tag=TAG).info(f"Voiceprint recognition configured: API={self.api_url}, speakers={len(self.speaker_ids)} total")
    
    def _parse_speakers(self) -> Dict[str, Dict[str, str]]:
        """Parse speaker configuration"""
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
                logger.bind(tag=TAG).warning(f"Failed to parse speaker configuration: {speaker_str}, error: {e}")
        return speaker_map
    
    async def identify_speaker(self, audio_data: bytes, session_id: str) -> Optional[str]:
        """Identify speaker"""
        if not self.enabled or not self.api_url or not self.api_key:
            logger.bind(tag=TAG).debug("Voiceprint recognition feature disabled or not configured, skipping recognition")
            return None
        
        try:
            api_start_time = time.monotonic()
            
            # Prepare request headers
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            # Prepare multipart/form-data data
            data = aiohttp.FormData()
            data.add_field('speaker_ids', ','.join(self.speaker_ids))
            data.add_field('file', audio_data, filename='audio.wav', content_type='audio/wav')
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            # Network request
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        speaker_id = result.get("speaker_id")
                        score = result.get("score", 0)
                        
                        total_elapsed_time = time.monotonic() - api_start_time
                        logger.bind(tag=TAG).info(f"Voiceprint recognition time: {total_elapsed_time:.3f}s")
                        
                        # Confidence check
                        if score < 0.5:
                            logger.bind(tag=TAG).warning(f"Low voiceprint recognition confidence: {score:.3f}")
                        
                        if speaker_id and speaker_id in self.speaker_map:
                            result_name = self.speaker_map[speaker_id]["name"]
                            return result_name
                        else:
                            logger.bind(tag=TAG).warning(f"Unrecognized speaker ID: {speaker_id}")
                            return "Unknown speaker"
                    else:
                        logger.bind(tag=TAG).error(f"Voiceprint recognition API error: HTTP {response.status}")
                        return None
        
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(f"Voiceprint recognition timeout: {elapsed:.3f}s")
            return None
        except Exception as e:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(f"Voiceprint recognition failed: {e}")
            return None
