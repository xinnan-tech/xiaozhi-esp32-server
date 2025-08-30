"""
CDN Handler for Audio Streaming
Provides API endpoints to test and use CDN functionality
"""
import json
from aiohttp import web
from config.logger import setup_logging

TAG = __name__


class CDNHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

    async def handle_get(self, request):
        """Handle GET requests for CDN status and testing"""
        try:
            # Import CDN helper
            from utils.cdn_helper import cdn, get_audio_url, is_cdn_ready
            
            # Get CDN status
            status = cdn.get_status()
            
            # Add some test URLs
            test_files = [
                "stories/Fantasy/goldilocks and the three bears.mp3",
                "stories/Educational/twinkle twinkle little star song.mp3",
                "stories/Fairy Tales/the boy who cried wolf.mp3"
            ]
            
            test_urls = {}
            for file in test_files:
                test_urls[file] = get_audio_url(file)
            
            response_data = {
                "cdn_status": status,
                "cdn_ready": is_cdn_ready(),
                "test_urls": test_urls,
                "message": "CDN is working correctly!" if is_cdn_ready() else "CDN not configured"
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error in CDN handler GET: {e}")
            return web.json_response(
                {"error": str(e), "message": "CDN handler error"}, 
                status=500
            )

    async def handle_post(self, request):
        """Handle POST requests for CDN URL generation"""
        try:
            # Parse request body
            data = await request.json()
            audio_file = data.get('audio_file', '')
            
            if not audio_file:
                return web.json_response(
                    {"error": "audio_file parameter required"}, 
                    status=400
                )
            
            # Import CDN helper
            from utils.cdn_helper import get_audio_url, get_cache_headers, is_cdn_ready
            
            # Generate CDN URL
            cdn_url = get_audio_url(audio_file)
            cache_headers = get_cache_headers()
            
            response_data = {
                "audio_file": audio_file,
                "cdn_url": cdn_url,
                "cache_headers": cache_headers,
                "cdn_ready": is_cdn_ready(),
                "message": "CDN URL generated successfully"
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error in CDN handler POST: {e}")
            return web.json_response(
                {"error": str(e), "message": "CDN URL generation failed"}, 
                status=500
            )

    async def handle_options(self, request):
        """Handle OPTIONS requests for CORS"""
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )