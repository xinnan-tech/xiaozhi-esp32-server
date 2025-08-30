#!/usr/bin/env python3
"""
Test CDN configuration and URL generation
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_cdn_config():
    """Test CDN configuration"""
    print("CDN CONFIGURATION TEST")
    print("=" * 50)
    
    # Check environment variables
    use_cdn = os.getenv("USE_CDN", "false")
    cloudfront_domain = os.getenv("CLOUDFRONT_DOMAIN", "")
    s3_base_url = os.getenv("S3_BASE_URL", "")
    
    print(f"USE_CDN: {use_cdn}")
    print(f"CLOUDFRONT_DOMAIN: {cloudfront_domain}")
    print(f"S3_BASE_URL: {s3_base_url}")
    
    # Test CDN Helper
    print("\nTesting CDN Helper...")
    try:
        from utils.cdn_helper import cdn, get_audio_url, is_cdn_ready
        
        status = cdn.get_status()
        print("CDN Helper Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Test URL generation
        test_file = "music/Hindi/Bum Bum Bole.mp3"
        generated_url = get_audio_url(test_file)
        
        print(f"\nTest File: {test_file}")
        print(f"Generated URL: {generated_url}")
        print(f"Is CDN Ready: {is_cdn_ready()}")
        
        # Verify the URL type
        if "cloudfront" in generated_url:
            print("SUCCESS: Using CloudFront URL")
        elif "s3.amazonaws.com" in generated_url:
            print("WARNING: Using direct S3 URL (will cause 403 errors)")
        else:
            print("UNKNOWN: Unexpected URL format")
            
        return generated_url
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_url_access(url):
    """Test URL accessibility"""
    if not url:
        return
        
    print(f"\nTesting URL Access...")
    print(f"URL: {url}")
    
    try:
        import requests
        response = requests.head(url, timeout=10)
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: URL is accessible")
            content_length = response.headers.get('content-length', 'unknown')
            content_type = response.headers.get('content-type', 'unknown')
            print(f"Content-Length: {content_length}")
            print(f"Content-Type: {content_type}")
        elif response.status_code == 403:
            print("ERROR: 403 Forbidden - Check CloudFront/S3 configuration")
        else:
            print(f"ERROR: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Network Error: {e}")

if __name__ == "__main__":
    url = test_cdn_config()
    test_url_access(url)