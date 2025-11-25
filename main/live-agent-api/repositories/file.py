"""
File repository - S3 storage operations
(Similar to User/Agent repositories but for file storage instead of database)
"""
from typing import Optional
from fastapi import UploadFile

from config import settings
from utils.ulid import ULID


class FileRepository:
    """
    File storage operations repository
    
    Handles S3 operations similar to how other repositories handle database operations.
    All methods are static and accept S3 client as first parameter (dependency injection).
    """
    
    @staticmethod
    async def upload(
        s3,  # S3 client from Depends(get_s3)
        file: UploadFile,
        folder: str = "uploads",
        custom_filename: Optional[str] = None
    ) -> str:
        """
        Upload file to S3 and return public URL
        
        Args:
            s3: S3 client (injected via Depends)
            file: File to upload
            folder: S3 folder path
            custom_filename: Optional custom filename (e.g., agent_id, voice_id)
                           If provided, uses this instead of generating ULID
            
        Returns:
            Public URL of uploaded file
            
        Example:
            # With custom filename (entity_id based)
            url = await FileRepository.upload(s3, file, "avatars", custom_filename="agent_123")
            # Result: avatars/agent_123.jpg
            
            # With auto-generated filename
            url = await FileRepository.upload(s3, file, "avatars")
            # Result: avatars/01JD8X0000ABC123DEF456GH.jpg
        """
        # Get file extension
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        
        # Generate filename
        if custom_filename:
            # Use custom filename (e.g., agent_id or voice_id)
            filename = f"{custom_filename}.{file_ext}" if file_ext else custom_filename
        else:
            # Generate unique filename using ULID
            filename = f"{ULID()}.{file_ext}" if file_ext else str(ULID())
        
        s3_key = f"{folder}/{filename}"
        
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer for potential reuse
        
        # Upload to S3
        await s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or 'application/octet-stream',
        )
        
        # Generate public URL
        url = f"{settings.S3_PUBLIC_BASE_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"
        return url


    @staticmethod
    async def delete(s3, url: str) -> bool:
        """
        Delete file from S3 by URL
        
        Args:
            s3: S3 client
            url: Full S3 URL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract S3 key from URL
            key = url.split(f"{settings.S3_PUBLIC_BASE_URL}/{settings.S3_BUCKET_NAME}/")[-1]
            
            await s3.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key
            )
            return True
        except Exception as e:
            print(f"Error deleting file from S3: {e}")
            return False
    
    # ========== Business-specific convenience methods ==========
    
    @staticmethod
    async def upload_avatar(s3, file: UploadFile, entity_id: str) -> str:
        """
        Upload agent/user avatar to S3
        
        Args:
            s3: S3 client
            file: Avatar file to upload
            entity_id: Entity ID (agent_id or user_id) used as filename
            
        Returns:
            Public URL of uploaded avatar
            
        Example:
            url = await FileRepository.upload_avatar(s3, file, "agent_01JD8X0000ABC")
            # Result: avatars/agent_01JD8X0000ABC.jpg
        """
        return await FileRepository.upload(s3, file, folder="agent_avatars", custom_filename=entity_id)
    
    @staticmethod
    async def upload_voice(s3, file: UploadFile, entity_id: str) -> str:
        """
        Upload voice audio file to S3
        
        Args:
            s3: S3 client
            file: Audio file to upload
            entity_id: Entity ID (voice_id) used as filename
            
        Returns:
            Public URL of uploaded audio
            
        Example:
            url = await FileRepository.upload_audio(s3, file, "voice_01JD8X0000XYZ")
            # Result: audio/voice_01JD8X0000XYZ.mp3
        """
        return await FileRepository.upload(s3, file, folder="voice_audios", custom_filename=entity_id)

    @staticmethod
    async def upload_chat_audio(
        s3, 
        audio_data: bytes, 
        agent_id: str,
        message_id: str,
        file_ext: str = "opus"
    ) -> str:
        """
        Upload chat audio to S3 (for chat messages)
        
        Args:
            s3: S3 client
            audio_data: Raw audio bytes (opus format)
            agent_id: Agent ID for organizing files
            message_id: Message ID (ULID) for unique filename
            file_ext: Audio file extension (default: opus)
            
        Returns:
            Public URL of uploaded audio
            
        Example:
            url = await FileRepository.upload_chat_audio(
                s3, audio_bytes, "agent_123", "01JD8X0000ABC"
            )
            # Result: https://s3.../chat-audio/agent_123/01JD8X0000ABC.opus
        """
        # Use message_id as filename (ULID is unique and time-ordered)
        filename = f"{message_id}.{file_ext}"
        s3_key = f"chat-audio/{agent_id}/{filename}"
        
        # Upload to S3
        await s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=audio_data,
            ContentType=f"audio/{file_ext}",
        )
        
        # Generate public URL
        url = f"{settings.S3_PUBLIC_BASE_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"
        return url

