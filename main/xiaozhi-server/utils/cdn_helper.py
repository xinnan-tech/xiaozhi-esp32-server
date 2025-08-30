"""
CDN Helper for Audio Streaming
Handles CloudFront CDN integration for audio file delivery
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CDNHelper:
    def __init__(self):
        self.use_cdn = os.getenv("USE_CDN", "false").lower() == "true"
        self.cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN", "")
        self.s3_base_url = os.getenv("S3_BASE_URL", "")
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME", "")
        
        # Fallback S3 URL if not provided
        if not self.s3_base_url and self.s3_bucket_name:
            region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            self.s3_base_url = f"https://{self.s3_bucket_name}.s3.{region}.amazonaws.com"
    
    def get_audio_url(self, audio_file: str) -> str:
        """
        Generate audio URL with CDN support
        
        Args:
            audio_file: Path to audio file (e.g., "uploads/audio123.mp3")
            
        Returns:
            Complete URL to audio file
        """
        import urllib.parse
        
        # Remove leading slash if present
        audio_file = audio_file.lstrip('/')
        
        # URL encode the file path to handle spaces and special characters
        encoded_audio_file = urllib.parse.quote(audio_file, safe='/')
        
        if self.use_cdn and self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{encoded_audio_file}"
        else:
            return f"{self.s3_base_url}/{encoded_audio_file}"
    
    def get_cache_headers(self) -> dict:
        """
        Get appropriate cache headers for audio responses
        """
        return {
            "Cache-Control": "public, max-age=86400",  # 24 hours
            "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD",
        }
    
    def is_cdn_enabled(self) -> bool:
        """Check if CDN is properly configured and enabled"""
        return self.use_cdn and bool(self.cloudfront_domain)
    
    def get_status(self) -> dict:
        """Get CDN configuration status for debugging"""
        return {
            "cdn_enabled": self.use_cdn,
            "cloudfront_domain": self.cloudfront_domain,
            "s3_base_url": self.s3_base_url,
            "s3_bucket": self.s3_bucket_name,
            "cdn_ready": self.is_cdn_enabled()
        }

# Global instance
cdn = CDNHelper()

# Convenience functions
def get_audio_url(audio_file: str) -> str:
    """Get audio URL with CDN support"""
    return cdn.get_audio_url(audio_file)

def get_cache_headers() -> dict:
    """Get cache headers for audio responses"""
    return cdn.get_cache_headers()

def is_cdn_ready() -> bool:
    """Check if CDN is ready to use"""
    return cdn.is_cdn_enabled()