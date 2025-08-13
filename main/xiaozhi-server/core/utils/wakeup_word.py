import os
import re
import yaml
import time
import hashlib
import portalocker
from typing import Dict


class FileLock:
    def __init__(self, file, timeout=5):
        self.file = file
        self.timeout = timeout
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        while True:
            try:
                portalocker.lock(
                    self.file, portalocker.LOCK_EX | portalocker.LOCK_NB)
                return self.file
            except portalocker.LockException:
                if time.time() - self.start_time > self.timeout:
                    raise TimeoutError("File lock acquisition timeout")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        portalocker.unlock(self.file)


class WakeupWordsConfig:
    def __init__(self):
        self.config_file = "data/.wakeup_words.yaml"
        self.assets_dir = "config/assets/wakeup_words"
        self._ensure_directories()

        self._config_cache = None
        self._last_load_time = 0
        self._cache_ttl = 1  # Cache TTL (seconds)
        self._lock_timeout = 5  # File lock timeout (seconds)

    def _ensure_directories(self):
        """Ensure necessary directories exist"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration file with caching mechanism"""
        current_time = time.time()

        # If cache is valid, return cache directly
        if (
            self._config_cache is not None
            and current_time - self._last_load_time < self._cache_ttl
        ):
            return self._config_cache

        try:
            with open(self.config_file, "a+") as f:
                with FileLock(f, timeout=self._lock_timeout):
                    f.seek(0)
                    content = f.read()
                    config = yaml.safe_load(content) if content else {}

                    self._config_cache = config
                    self._last_load_time = current_time
                    return config

        except (TimeoutError, IOError) as e:
            print(f"Failed to load configuration file: {e}")
            return {}
        except Exception as e:
            print(
                f"Unknown error occurred while loading configuration file: {e}")
            return {}

    def _save_config(self, config: Dict):
        """Save configuration to file with file lock protection"""
        try:
            with open(self.config_file, "w") as f:
                with FileLock(f, timeout=self._lock_timeout):
                    yaml.dump(config, f, allow_unicode=True)
                    self._config_cache = config
                    self._last_load_time = time.time()

        except (TimeoutError, IOError) as e:
            print(f"Failed to save configuration file: {e}")
            raise
        except Exception as e:
            print(
                f"Unknown error occurred while saving configuration file: {e}")
            raise

    def get_wakeup_response(self, voice: str) -> Dict:
        """Get wakeup word response configuration"""
        voice = hashlib.md5(voice.encode()).hexdigest()
        config = self._load_config()

        if not config or voice not in config:
            return None

        # Check file size
        file_path = config[voice]["file_path"]
        if not os.path.exists(file_path) or os.stat(file_path).st_size < (15 * 1024):
            return None

        return config[voice]

    def update_wakeup_response(self, voice: str, file_path: str, text: str):
        """Update wakeup word response configuration"""
        try:
            # Filter emoji symbols
            filtered_text = re.sub(
                r'[\U0001F600-\U0001F64F\U0001F900-\U0001F9FF]', '', text)

            config = self._load_config()
            voice_hash = hashlib.md5(voice.encode()).hexdigest()

            config[voice_hash] = {
                "voice": voice,
                "file_path": file_path,
                "time": time.time(),
                "text": filtered_text,
            }

            self._save_config(config)

        except Exception as e:
            print(f"Failed to update wakeup word response configuration: {e}")
            raise

    def generate_file_path(self, voice: str) -> str:
        """Generate audio file path using voice hash as filename"""
        try:
            # Generate hash of voice
            voice_hash = hashlib.md5(voice.encode()).hexdigest()
            file_path = os.path.join(self.assets_dir, f"{voice_hash}.wav")

            # If file already exists, delete it first
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete existing audio file: {e}")
                    raise

            return file_path

        except Exception as e:
            print(f"Failed to generate audio file path: {e}")
            raise
