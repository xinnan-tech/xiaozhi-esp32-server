"""
CDN Download Manager for xiaozhi-server
Manages downloading CDN files for local streaming to solve completion signal issues
"""

import asyncio
import tempfile
import aiohttp
import aiofiles
from pathlib import Path
import logging
import hashlib
import json
import time
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

TAG = __name__


class CDNDownloadManager:
    """Basic CDN file download manager"""
    
    def __init__(self, temp_dir: str = None):
        """
        Initialize CDN download manager
        
        Args:
            temp_dir: Directory for temporary files (default: system temp)
        """
        if temp_dir:
            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = None
    
    async def download_file(self, cdn_url: str, conn) -> str:
        """
        Download CDN file to temporary location
        
        Args:
            cdn_url: CDN URL to download
            conn: Connection object for logging
            
        Returns:
            str: Path to downloaded temporary file
            
        Raises:
            Exception: If download fails
        """
        try:
            conn.logger.bind(tag=TAG).info(f"Starting CDN download: {cdn_url}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", 
                dir=self.temp_dir,
                delete=False
            ) as tmp_file:
                temp_path = tmp_file.name
                
                # Download with progress tracking
                timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(cdn_url) as response:
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        conn.logger.bind(tag=TAG).debug(f"CDN file size: {total_size} bytes")
                        
                        async for chunk in response.content.iter_chunked(8192):
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Log progress every 25%
                            if total_size > 0 and downloaded % (total_size // 4) < 8192:
                                progress = (downloaded / total_size) * 100
                                conn.logger.bind(tag=TAG).debug(f"Download progress: {progress:.1f}%")
                
                conn.logger.bind(tag=TAG).info(f"CDN download completed: {downloaded} bytes -> {temp_path}")
                
                # Schedule cleanup after 10 minutes
                asyncio.create_task(self._cleanup_file(temp_path, 600))
                
                return temp_path
                
        except asyncio.TimeoutError:
            conn.logger.bind(tag=TAG).error(f"CDN download timeout: {cdn_url}")
            raise Exception(f"Download timeout for {cdn_url}")
            
        except aiohttp.ClientError as e:
            conn.logger.bind(tag=TAG).error(f"CDN download network error: {e}")
            raise Exception(f"Network error downloading {cdn_url}: {e}")
            
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"CDN download failed: {e}")
            raise Exception(f"Failed to download {cdn_url}: {e}")
    
    async def _cleanup_file(self, filepath: str, delay: int):
        """
        Clean up temporary file after delay
        
        Args:
            filepath: Path to file to clean up
            delay: Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        try:
            file_path = Path(filepath)
            if file_path.exists():
                file_path.unlink()
                logging.debug(f"Cleaned up temporary CDN file: {filepath}")
        except Exception as e:
            logging.warning(f"Failed to cleanup CDN temp file {filepath}: {e}")


class SmartCDNCacheManager(CDNDownloadManager):
    """Enhanced CDN manager with intelligent caching"""
    
    def __init__(self, cache_dir: str = "./cache/cdn_audio", max_cache_size_mb: int = 500):
        """
        Initialize smart cache manager
        
        Args:
            cache_dir: Directory for cached files
            max_cache_size_mb: Maximum cache size in MB
        """
        super().__init__()
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024
        self.cache_index_file = self.cache_dir / "cache_index.json"
        self.cache_index = self._load_cache_index()
        
        logging.info(f"CDN cache initialized: {cache_dir} (max: {max_cache_size_mb}MB)")
    
    def _load_cache_index(self) -> Dict[str, Any]:
        """Load cache index from disk"""
        try:
            if self.cache_index_file.exists():
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load cache index: {e}")
        return {}
    
    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            with open(self.cache_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save cache index: {e}")
    
    def _get_cache_key(self, cdn_url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(cdn_url.encode()).hexdigest()
    
    def _extract_title_from_url(self, cdn_url: str) -> str:
        """Extract title from CDN URL"""
        try:
            # Extract filename from URL path
            from urllib.parse import urlparse, unquote
            parsed = urlparse(cdn_url)
            filename = Path(unquote(parsed.path)).name
            # Remove extension and decode URL encoding
            title = Path(filename).stem
            return title
        except Exception:
            return "Unknown"
    
    async def get_or_download(self, cdn_url: str, conn) -> str:
        """
        Get from cache or download if not cached
        
        Args:
            cdn_url: CDN URL to get/download
            conn: Connection object for logging
            
        Returns:
            str: Path to local file (cached or downloaded)
        """
        cache_key = self._get_cache_key(cdn_url)
        cache_path = self.cache_dir / f"{cache_key}.mp3"
        
        # Check if cached and valid
        if cache_key in self.cache_index:
            cache_info = self.cache_index[cache_key]
            
            if cache_path.exists() and cache_path.stat().st_size > 0:
                # Update access statistics
                cache_info['last_accessed'] = datetime.now().isoformat()
                cache_info['access_count'] = cache_info.get('access_count', 0) + 1
                self._save_cache_index()
                
                title = cache_info.get('title', 'Unknown')
                conn.logger.bind(tag=TAG).info(f"CDN cache hit: {title}")
                return str(cache_path)
        
        # Not cached or invalid, download
        conn.logger.bind(tag=TAG).info(f"CDN cache miss, downloading: {cdn_url}")
        
        try:
            # Download to temp first
            temp_path = await super().download_file(cdn_url, conn)
            
            # Cross-platform move to cache (handles Windows cross-drive issue)
            try:
                # Try rename first (faster on same drive)
                Path(temp_path).rename(cache_path)
            except OSError:
                # If rename fails (cross-drive on Windows), use copy + delete
                shutil.copy2(temp_path, cache_path)
                Path(temp_path).unlink()  # Delete temp file after copy
            
            # Update cache index
            self.cache_index[cache_key] = {
                'url': cdn_url,
                'path': str(cache_path),
                'size': cache_path.stat().st_size,
                'created': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'access_count': 1,
                'title': self._extract_title_from_url(cdn_url)
            }
            self._save_cache_index()
            
            # Manage cache size
            await self._manage_cache_size()
            
            conn.logger.bind(tag=TAG).info(f"CDN file cached: {cache_path}")
            return str(cache_path)
            
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"CDN download/cache failed: {e}")
            raise
    
    async def _manage_cache_size(self):
        """Remove old files if cache exceeds size limit"""
        try:
            total_size = sum(
                info['size'] for info in self.cache_index.values() 
                if Path(info['path']).exists()
            )
            
            if total_size > self.max_cache_size:
                # Sort by last accessed (LRU - Least Recently Used)
                sorted_items = sorted(
                    self.cache_index.items(),
                    key=lambda x: x[1].get('last_accessed', '1970-01-01')
                )
                
                # Remove oldest 25% of files
                to_remove = sorted_items[:len(sorted_items)//4] if len(sorted_items) > 4 else sorted_items[:1]
                
                for cache_key, info in to_remove:
                    cache_path = Path(info['path'])
                    if cache_path.exists():
                        cache_path.unlink()
                        
                    del self.cache_index[cache_key]
                    title = info.get('title', cache_key)
                    logging.info(f"Evicted from CDN cache: {title}")
                
                self._save_cache_index()
                logging.info(f"CDN cache cleanup: removed {len(to_remove)} files")
                
        except Exception as e:
            logging.error(f"CDN cache cleanup failed: {e}")
    
    async def download_with_retry(self, cdn_url: str, conn, max_retries: int = 3) -> Optional[str]:
        """
        Download with automatic retry on failure
        
        Args:
            cdn_url: CDN URL to download
            conn: Connection object for logging
            max_retries: Maximum retry attempts
            
        Returns:
            str: Path to local file, or None if all attempts failed
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self.get_or_download(cdn_url, conn)
                
            except Exception as e:
                last_error = e
                conn.logger.bind(tag=TAG).warning(
                    f"CDN download attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
        
        # All retries failed
        conn.logger.bind(tag=TAG).error(f"CDN download failed after {max_retries} attempts: {last_error}")
        return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_files = len(self.cache_index)
            total_size = sum(info['size'] for info in self.cache_index.values())
            
            most_accessed = sorted(
                self.cache_index.items(),
                key=lambda x: x[1].get('access_count', 0),
                reverse=True
            )[:5]
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_usage_percent': round((total_size / self.max_cache_size) * 100, 1),
                'most_played': [
                    {
                        'title': info.get('title', 'Unknown'),
                        'count': info.get('access_count', 0)
                    }
                    for _, info in most_accessed
                ]
            }
        except Exception as e:
            logging.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}
    
    async def preload_popular_content(self, urls_and_titles: list, conn):
        """
        Preload popular content during off-peak hours
        
        Args:
            urls_and_titles: List of (url, title) tuples to preload
            conn: Connection object for logging
        """
        conn.logger.bind(tag=TAG).info(f"Preloading {len(urls_and_titles)} popular items")
        
        for i, (url, title) in enumerate(urls_and_titles):
            try:
                await self.get_or_download(url, conn)
                conn.logger.bind(tag=TAG).debug(f"Preloaded {i+1}/{len(urls_and_titles)}: {title}")
                
                # Small delay to avoid overwhelming the CDN
                await asyncio.sleep(0.5)
                
            except Exception as e:
                conn.logger.bind(tag=TAG).warning(f"Failed to preload {title}: {e}")
        
        conn.logger.bind(tag=TAG).info("Content preloading completed")


# Global instance - can be configured via environment/config
cdn_manager = SmartCDNCacheManager()


async def download_cdn_file(cdn_url: str, conn, use_cache: bool = True) -> Optional[str]:
    """
    Convenience function to download CDN file
    
    Args:
        cdn_url: CDN URL to download
        conn: Connection object for logging
        use_cache: Whether to use caching (default: True)
        
    Returns:
        str: Path to local file, or None if failed
    """
    try:
        if use_cache:
            return await cdn_manager.download_with_retry(cdn_url, conn)
        else:
            basic_manager = CDNDownloadManager()
            return await basic_manager.download_file(cdn_url, conn)
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"CDN download failed: {e}")
        return None