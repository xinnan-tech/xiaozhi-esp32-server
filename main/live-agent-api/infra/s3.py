"""
S3 infrastructure - AWS S3 connection and session management
"""
from typing import AsyncGenerator
import aioboto3
from types import SimpleNamespace

from config import settings


s3_session = aioboto3.Session()


async def get_s3() -> AsyncGenerator[SimpleNamespace, None]:
    """
    Dependency to get S3 client
    
    Usage:
        @router.post("/upload")
        async def upload(s3 = Depends(get_s3)):
            await s3.put_object(...)
    
    Returns:
        S3 client with async context management
    """
    async with s3_session.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL
    ) as client:
        yield client


async def init_s3():
    """
    Initialize S3 connection and verify bucket access
    (called in lifespan startup)
    """
    try:
        async with s3_session.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL
        ) as client:
            # Verify bucket exists and accessible
            await client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        print(f"S3 connection verified: bucket '{settings.S3_BUCKET_NAME}'")
    except Exception as e:
        print(f"Warning: S3 connection verification failed: {e}")
        print("S3 operations may not work properly")


async def close_s3():
    """
    Close S3 connections (called in lifespan shutdown)
    
    Note: aioboto3 handles cleanup automatically via context managers,
    but this function is provided for symmetry with database layer
    """
    print("S3 connections closed")

