from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from fishaudio import AsyncFishAudio
from fishaudio.types import PaginatedResponse, Voice as FishVoice, Sample as FishSample

from repositories import VoiceModel, Voice
from utils.ulid import generate_voice_id

from repositories import FileRepository
from datetime import datetime, timezone
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
        Clone a voice using Fish Audio API, store audio, and save to database
        
        Args:
            db: Database session
            s3: S3 client for storing audio
            fish_client: Fish Audio client
            owner_id: User ID
            audio_file: Audio file to clone
            text: Optional transcription text
            
        Returns:
            Created VoiceModel
        """
        # Generate voice_id for our system
        voice_id = generate_voice_id()
        
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Reset file pointer for S3 upload
        await audio_file.seek(0)
        
        # Upload audio to S3 for storage (using voice_id as filename)
        
        sample_url = await FileRepository.upload(
            s3=s3,
            file=audio_file,
            folder="voice_samples",
            custom_filename=voice_id
        )
        
        # Call Fish Audio API to clone voice
        fish_voice: FishVoice = await fish_client.voices.create(
            title=f"live_agent_{voice_id}",
            voices=[audio_content],
            texts=[text] if text else None,
            train_mode="fast",
            visibility="private",
            enhance_audio_quality=True
        )
        
        # Create voice record in database
        
        default_name = f"{owner_id}'s Cloned Voice {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        
        voice = await Voice.create(
            db=db,
            voice_id=fish_voice.id,  # Use Fish Audio voice ID
            owner_id=owner_id,
            name=default_name,
            desc="",  # Empty description, to be updated later
            sample_url=sample_url,
            sample_text=text
        )
        
        return voice
    
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
        voice_id: str,
        owner_id: str
    ) -> bool:
        """
        Remove a voice from user's my voices
        
        Args:
            db: Database session
            voice_id: Internal voice ID
            owner_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        deleted = await Voice.delete(db=db, voice_id=voice_id, owner_id=owner_id)
        
        if not deleted:
            from utils.exceptions import NotFoundException
            raise NotFoundException(f"Voice {voice_id} not found or not owned by user")
        
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

