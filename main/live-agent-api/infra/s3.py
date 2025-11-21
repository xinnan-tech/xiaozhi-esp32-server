"""
S3 infrastructure - AWS S3 connection and session management
"""
import aioboto3

from config import settings


s3_session = aioboto3.Session()
_s3_client = None


async def get_s3() :
    """
    Dependency to get S3 client
    
    Returns:
        S3 client
    """
    if _s3_client is None:
        raise RuntimeError("S3 client not initialized. Call init_s3() first.")
    return _s3_client

async def init_s3():
    """
    Initialize S3 connection and verify bucket access
    (called in lifespan startup)
    """
    global _s3_client
    try:
        _s3_client = await s3_session.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL
        ).__aenter__()
        
        # Verify bucket exists and accessible
        await _s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        print(f"S3 connection verified: bucket '{settings.S3_BUCKET_NAME}'")
    except Exception as e:
        print(f"Warning: S3 connection verification failed: {e}")
        print("S3 operations may not work properly")
        raise


async def close_s3():
    """
    Close S3 connections (called in lifespan shutdown)
    
    Note: aioboto3 handles cleanup automatically via context managers,
    but this function is provided for symmetry with database layer
    """
    global _s3_client
    if _s3_client:
        await _s3_client.__aexit__(None, None, None)
        _s3_client = None
    print("S3 connections closed")

