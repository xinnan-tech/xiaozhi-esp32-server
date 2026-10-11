import os
import uuid
import requests
import tempfile
import asyncio
from datetime import datetime
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

try:
    # Try to import the kokoro-tts package
    import kokoro_tts
    KOKORO_AVAILABLE = True
except ImportError:
    try:
        # Fallback: check if kokoro-tts CLI is available
        import subprocess
        result = subprocess.run(['kokoro-tts', '--version'], capture_output=True, text=True, timeout=5)
        KOKORO_CLI_AVAILABLE = result.returncode == 0
        KOKORO_AVAILABLE = KOKORO_CLI_AVAILABLE
    except (ImportError, subprocess.TimeoutExpired, FileNotFoundError):
        KOKORO_AVAILABLE = False

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        if not KOKORO_AVAILABLE:
            raise ImportError("Kokoro TTS package not installed. Please run: pip install kokoro-tts==2.3.0")
        
        # Configuration parameters
        self.api_url = config.get("api_url", "http://localhost:8000/api/v1/audio/speech")
        self.api_key = config.get("api_key", "")  # Optional for local deployment
        self.voice = config.get("voice", "af_heart")  # Default voice
        self.model = config.get("model", "model_fp32")  # Default model
        self.response_format = config.get("response_format", "mp3")
        self.speed = float(config.get("speed", "1.0"))
        self.language = config.get("language", "en-us")
        self.use_api = config.get("use_api", True)  # Use API vs package
        
        # Check if we have the Python package or just CLI
        self.has_python_package = 'kokoro_tts' in globals()
        
        # If not using API and no Python package, force CLI mode
        if not self.use_api and not self.has_python_package:
            logger.bind(tag=TAG).warning("Kokoro TTS Python package not available, falling back to CLI mode")
            self.use_cli_fallback = True
        else:
            self.use_cli_fallback = False
        
        # Audio file configuration
        self.audio_file_type = self.response_format
        self.output_file = config.get("output_dir", "tmp/")
        
        logger.debug(
            f"Kokoro TTS parameters initialized: voice={self.voice}, model={self.model}, "
            f"format={self.response_format}, speed={self.speed}, language={self.language}, "
            f"use_api={self.use_api}, api_url={self.api_url}"
        )
        
        # Validate API key if using API mode
        if self.use_api and self.api_key:
            model_key_msg = check_model_key("Kokoro TTS", self.api_key)
            if model_key_msg:
                logger.bind(tag=TAG).error(model_key_msg)
        
        # Log configuration for debugging
        logger.bind(tag=TAG).info(f"Kokoro TTS initialized with voice: {self.voice}, model: {self.model}")

    def generate_filename(self, extension=None):
        if not extension:
            extension = f".{self.response_format}"
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        logger.bind(tag=TAG).debug(f"Sending Kokoro TTS request with voice: {self.voice}, text length: {len(text)}")
        
        if self.use_api:
            return await self._api_text_to_speak(text, output_file)
        elif self.has_python_package and not self.use_cli_fallback:
            return await self._package_text_to_speak(text, output_file)
        else:
            return await self._cli_text_to_speak(text, output_file)

    async def _api_text_to_speak(self, text, output_file):
        """Use Kokoro TTS API for text-to-speech conversion"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "input": text,
            "voice": self.voice,
            "model": self.model,
            "response_format": self.response_format,
            "speed": self.speed
        }
        
        logger.bind(tag=TAG).debug(f"Making Kokoro TTS API request to: {self.api_url}")
        
        try:
            # requests is blocking; keep the shared event loop free
            response = await asyncio.to_thread(
                requests.post, self.api_url, json=data, headers=headers, timeout=30
            )
            
            if response.status_code == 200:
                logger.bind(tag=TAG).debug(f"Kokoro TTS API request successful, audio size: {len(response.content)} bytes")
                
                if output_file:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    with open(output_file, "wb") as f:
                        f.write(response.content)
                    
                    logger.bind(tag=TAG).debug(f"Kokoro TTS audio saved to: {output_file}")
                else:
                    return response.content
            else:
                # Parse error response for better error messages
                error_detail = "Unknown error"
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", response.text)
                except:
                    error_detail = response.text
                
                if response.status_code == 401:
                    error_msg = f"Kokoro TTS API authentication failed: {error_detail}. Please check your API key."
                elif response.status_code == 429:
                    error_msg = f"Kokoro TTS API rate limit exceeded: {error_detail}. Please wait and try again."
                elif response.status_code == 400:
                    error_msg = f"Kokoro TTS API bad request: {error_detail}. Please check your configuration."
                else:
                    error_msg = f"Kokoro TTS API request failed ({response.status_code}): {error_detail}"
                
                logger.bind(tag=TAG).error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Kokoro TTS API request error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Kokoro TTS API unexpected error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)

    async def _package_text_to_speak(self, text, output_file):
        """Use Kokoro TTS Python package for text-to-speech conversion"""
        try:
            logger.bind(tag=TAG).debug(f"Using Kokoro TTS Python package for synthesis")
            
            # Track if we need to return audio data
            return_audio_data = output_file is None
            
            # Generate output file if not provided
            if not output_file:
                output_file = self.generate_filename()
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Delegate to the synchronous worker (kokoro-tts CLI in a thread)
            logger.bind(tag=TAG).debug(f"Generating audio with Kokoro TTS package")
            
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._generate_with_package, 
                text, 
                output_file
            )
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.bind(tag=TAG).debug(f"Kokoro TTS package synthesis successful: {output_file}")
                
                # If no output_file was provided originally, return the audio data
                if return_audio_data:
                    with open(output_file, "rb") as f:
                        audio_data = f.read()
                    # Clean up temporary file
                    os.unlink(output_file)
                    return audio_data
            else:
                raise Exception("Kokoro TTS package failed to generate audio")
                
        except Exception as e:
            error_msg = f"Kokoro TTS package error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
    
    def _generate_with_package(self, text, output_file):
        """Synchronous worker: run the kokoro-tts CLI as a subprocess.

        The kokoro_tts python distribution exposes no stable documented
        in-process API, so the "package" path shells out to its console
        script in a worker thread (same engine as the async CLI path).
        """
        try:
            import subprocess
            
            # Create temporary input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_input:
                temp_input.write(text)
                temp_input_path = temp_input.name
            
            try:
                # Build CLI command
                cmd = [
                    "kokoro-tts",
                    temp_input_path,
                    output_file,
                    "--voice", self.voice,
                    "--lang", self.language,
                    "--speed", str(self.speed)
                ]
                
                logger.bind(tag=TAG).debug(f"Running Kokoro TTS package command: {' '.join(cmd)}")
                
                # Run CLI command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    raise Exception(f"Kokoro TTS command failed: {result.stderr}")
                    
            finally:
                # Clean up temporary input file
                try:
                    os.unlink(temp_input_path)
                except:
                    pass
                    
        except Exception as e:
            raise Exception(f"Package generation failed: {str(e)}")

    async def _cli_text_to_speak(self, text, output_file):
        """Use Kokoro TTS CLI for text-to-speech conversion"""
        
        try:
            # Create temporary input file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_input:
                temp_input.write(text)
                temp_input_path = temp_input.name
            
            # Generate output file if not provided; remember who owns it so
            # the "return raw audio" path below can actually fire
            return_audio_data = not output_file
            if not output_file:
                output_file = self.generate_filename()
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Build CLI command
            cmd = [
                "kokoro-tts",
                temp_input_path,
                output_file,
                "--voice", self.voice,
                "--lang", self.language,
                "--speed", str(self.speed)
            ]
            
            logger.bind(tag=TAG).debug(f"Running Kokoro TTS CLI command: {' '.join(cmd)}")
            
            # Run CLI command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.bind(tag=TAG).debug(f"Kokoro TTS CLI successful, output saved to: {output_file}")
                
                # If no output_file was provided originally, return the audio data
                if return_audio_data:
                    with open(output_file, "rb") as f:
                        audio_data = f.read()
                    # Clean up temporary output file
                    os.unlink(output_file)
                    return audio_data
            else:
                error_msg = f"Kokoro TTS CLI failed: {stderr.decode()}"
                logger.bind(tag=TAG).error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Kokoro TTS CLI error: {str(e)}"
            logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        finally:
            # Clean up temporary input file
            if 'temp_input_path' in locals():
                try:
                    os.unlink(temp_input_path)
                except:
                    pass
