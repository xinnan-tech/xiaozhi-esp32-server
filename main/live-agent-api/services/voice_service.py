from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from fishaudio import AsyncFishAudio
from fishaudio.types import PaginatedResponse, Voice as FishVoice, Sample as FishSample

from repositories import VoiceModel, Voice

from repositories import FileRepository
from datetime import datetime, timezone
from config.logger import setup_logging
from utils.exceptions import NotFoundException


TAG = __name__
logger = setup_logging(TAG)

# Default sample text for TTS preview when user doesn't provide text
DEFAULT_SAMPLE_TEXT = {
    "en": "The only way to do great work is to love what you do.",
    "zh": "只有热爱才能做出伟大的工作。",
    "ja": "偉大な仕事をする唯一の方法は、あなたが何を愛するかです。"
} 
class VoiceService:
    """Voice service layer"""
    
    async def get_discover_voices(
        self,
        fish_client: AsyncFishAudio,
        title: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        language: Optional[str] = None
    ) -> Tuple[List[FishVoice], bool]:
        """
        Get voices from Fish Audio platform (discover tab)
        Sorted by task_count (popularity)
        
        Returns:
            Tuple of (voice_list, total_count)
        """
        # Call Fish Audio API to list voices
        response: PaginatedResponse[FishVoice] = await fish_client.voices.list(
            page_size=page_size,
            page_number=page,
            title=title,
            sort_by="task_count",  # Sort by popularity
            language=language
        )

        has_more = response.total > page * page_size
        
        return response.items, has_more
    
    async def get_default_voices(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20
    ) -> List[VoiceModel]:
        """
        Get platform default voices (default tab)
        TODO: Implement after PM discussion
        
        Returns:
            List of VoiceModel objects
        """
        skip = (page - 1) * page_size
        voices = await Voice.get_list(
            db,
            owner_id=None,
            category="default",
            skip=skip,
            limit=page_size
        )
        return voices
    
    async def get_my_voices(
        self,
        db: AsyncSession,
        owner_id: str,
        cursor: Optional[str] = None,
        page_size: int = 20
    ) -> Tuple[List[VoiceModel], Optional[str], bool]:
        """
        Get user's custom voices with cursor-based pagination
        
        Args:
            db: Database session
            owner_id: User ID
            cursor: Pagination cursor (ISO datetime string)
            page_size: Number of items per page
            
        Returns:
            Tuple of (voices, next_cursor, has_more)
        """
        voices, next_cursor, has_more = await Voice.get_list(
            db,
            owner_id=owner_id,
            cursor=cursor,
            limit=page_size
        )

        return voices, next_cursor, has_more
    
    async def clone_voice(
        self,
        db: AsyncSession,
        s3,  # S3 client for storing audio
        fish_client: AsyncFishAudio,
        owner_id: str,
        audio_file: UploadFile,
        text: Optional[str] = None
    ) -> VoiceModel:
        """
        Clone a voice using Fish Audio API, generate TTS preview, and save to database
        
        Flow:
        1. Clone voice from uploaded audio + optional text
        2. Generate TTS preview audio using the new voice (with provided or default text)
        3. Upload TTS preview to S3 as sample_url
        4. Create voice record in database
        
        Args:
            db: Database session
            s3: S3 client for storing audio
            fish_client: Fish Audio client
            owner_id: User ID
            audio_file: Audio file to clone
            text: Optional transcription text (also used for TTS preview)
            
        Returns:
            Created VoiceModel
            
        Raises:
            InternalServerException: When any downstream service fails
        """
        from utils.exceptions import InternalServerException
        
        fish_voice_id: Optional[str] = None
        sample_url: Optional[str] = None
        
        try:
            # Read audio file content for cloning
            audio_content = await audio_file.read()
            logger.bind(tag=TAG).info(f"Audio content length: {len(audio_content)} bytes")
            
            # Step 1: Clone voice using Fish Audio API
            fish_voice: FishVoice = await fish_client.voices.create(
                title=f"live_agent_{owner_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                voices=[audio_content],
                texts=[text] if text else None,
                train_mode="fast",
                visibility="private",
                enhance_audio_quality=True
            )
            fish_voice_id = fish_voice.id
            language = fish_voice.languages[0] if len(fish_voice.languages) > 0 else "en"
            sample_text = DEFAULT_SAMPLE_TEXT[language]
            
            # Step 2: Generate TTS preview using the new voice
            logger.bind(tag=TAG).info(f"Generating TTS preview with voice {fish_voice_id}")
            audio_bytes = await fish_client.tts.convert(
                text=sample_text,
                reference_id=fish_voice_id,
                format="mp3"
            )
            logger.bind(tag=TAG).info(f"TTS preview generated, size: {len(audio_bytes)} bytes")
            
            # Step 3: Upload TTS preview audio to S3
            sample_url = await FileRepository.upload_voice_sample(
                s3=s3,
                audio_data=audio_bytes,
                voice_id=fish_voice_id,
                file_ext="mp3"
            )
            logger.bind(tag=TAG).info(f"TTS preview uploaded to S3: {sample_url}")
            
            # Step 4: Create voice record in database
            voice = await Voice.create(
                db=db,
                voice_id=fish_voice_id,
                owner_id=owner_id,
                name="Cloned Voice",
                desc="",
                sample_url=sample_url,
                sample_text=sample_text
            )
            
            return voice
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Clone voice failed: {e}")
            # Cleanup created resources based on what was successfully created
            if sample_url:
                await self._cleanup_s3_file(s3, sample_url)
            if fish_voice_id:
                await self._cleanup_fish_voice(fish_client, fish_voice_id)
            raise InternalServerException(f"Voice cloning failed: {str(e)}")
    
    async def _cleanup_fish_voice(self, fish_client: AsyncFishAudio, voice_id: str) -> None:
        """Cleanup helper: delete voice from Fish Audio"""
        try:
            await fish_client.voices.delete(voice_id)
            logger.bind(tag=TAG).info(f"Cleanup: deleted Fish Audio voice {voice_id}")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Cleanup failed: could not delete Fish Audio voice {voice_id}: {e}")
    
    async def _cleanup_s3_file(self, s3, url: str) -> None:
        """Cleanup helper: delete file from S3"""
        try:
            await FileRepository.delete(s3, url)
            logger.bind(tag=TAG).info(f"Cleanup: deleted S3 file {url}")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Cleanup failed: could not delete S3 file {url}: {e}")
    
    async def add_voice(
        self,
        db: AsyncSession,
        fish_client: AsyncFishAudio,
        owner_id: str,
        voice_id: str,
        name: str,
        desc: str,
        sample_url: Optional[str] = None,
        sample_text: Optional[str] = None
    ) -> VoiceModel:
        """
        Add a Fish Audio voice to user's my voices
        
        Args:
            db: Database session
            fish_client: Fish Audio client
            owner_id: User ID
            voice_id: Audio voice ID
            name: Voice name
            desc: Voice description
            sample_url: Optional URL of stored audio sample (for cloned voices)
            sample_text: Optional transcription text (for cloned voices)
            
        Returns:
            Created VoiceModel
        """
        # Verify the Fish voice exists and get its info
        fish_voice = await fish_client.voices.get(voice_id)
        if not fish_voice:
            from utils.exceptions import NotFoundException
            raise NotFoundException(f"Fish voice {voice_id} not found")

        # Create voice record in database using Fish voice ID directly
        voice = await Voice.create(
            db=db,
            voice_id=voice_id,  # Use Fish Audio voice ID directly
            owner_id=owner_id,
            name=name,
            desc=desc,
            sample_url=sample_url,
            sample_text=sample_text
        )
        
        return voice
    
    async def remove_voice(
        self,
        db: AsyncSession,
        s3,
        fish_client: AsyncFishAudio,
        voice_id: str,
        owner_id: str
    ) -> bool:
        """
        Remove a voice completely: database, S3, and Fish Audio
        
        Args:
            db: Database session
            s3: S3 client
            fish_client: Fish Audio client
            voice_id: Voice ID
            owner_id: User ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundException: If voice not found or not owned by user
        """
        
        # Get voice record first to get sample_url for S3 cleanup
        voice = await Voice.get_by_voice_and_owner(db=db, voice_id=voice_id, owner_id=owner_id)
        if not voice:
            raise NotFoundException(f"Voice {voice_id} not found or not owned by user")
        
        sample_url = voice.sample_url
        
        # Delete from database first
        deleted = await Voice.delete(db=db, voice_id=voice_id, owner_id=owner_id)
        if not deleted:
            raise NotFoundException(f"Voice {voice_id} not found or not owned by user")
        
        # Cleanup S3 file (best effort, don't fail if cleanup fails)
        try:
            if sample_url:
                await self._cleanup_s3_file(s3, sample_url)
            await self._cleanup_fish_voice(fish_client, voice_id)
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Cleanup failed: {e}")
            return False
        return True
    
    async def update_voice(
        self,
        db: AsyncSession,
        voice_id: str,
        owner_id: str,
        name: Optional[str] = None,
        desc: Optional[str] = None
    ) -> VoiceModel:
        """
        Update voice name and/or description
        
        Args:
            db: Database session
            voice_id: Voice ID
            owner_id: User ID
            name: New voice name (optional)
            desc: New voice description (optional)
            
        Returns:
            Updated VoiceModel
        """
        # Get existing voice to verify ownership
        voice = await Voice.get_by_voice_and_owner(
            db=db,
            voice_id=voice_id,
            owner_id=owner_id
        )
        
        if not voice:
            from utils.exceptions import NotFoundException
            raise NotFoundException(f"Voice {voice_id} not found or not owned by user")
        
        # Update only provided fields
        updated_voice = await Voice.update(
            db=db,
            voice_id=voice_id,
            owner_id=owner_id,
            name=name,
            desc=desc
        )
        
        return updated_voice


voice_service = VoiceService()

