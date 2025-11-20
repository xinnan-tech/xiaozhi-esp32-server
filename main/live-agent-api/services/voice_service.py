from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from fishaudio import AsyncFishAudio
from fishaudio.types import PaginatedResponse, Voice as FishVoice

from repositories import VoiceModel, Voice
from utils.ulid import generate_voice_id
class VoiceService:
    """Voice service layer"""
    
    async def get_discover_voices(
        self,
        fish_client: AsyncFishAudio,
        title: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        language: str = "en"
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
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[VoiceModel], int]:
        """
        Get user's custom voices (my_voices tab)
        
        Returns:
            List of VoiceModel objects
        """
        skip = (page - 1) * page_size
        voices = await Voice.get_list(
            db,
            owner_id=owner_id,
            skip=skip,
            limit=page_size
        )

        count = await Voice.count(db, owner_id=owner_id)
        return voices, count
    
    async def clone_voice(
        self,
        fish_client: AsyncFishAudio,
        audio_file: UploadFile,
        text: Optional[str] = None
    ) -> VoiceModel:
        """
        Clone a voice using Fish Audio API
        
        Args:
            db: Database session
            fish_client: Fish Audio client
            name: Voice name
            owner_id: User ID
            name: Voice name
            audio_file: Audio file to clone
            text: Optional transcription text
            
        Returns:
            Created VoiceModel
        """
        # Read audio file content
        audio_content = await audio_file.read()
        voice_id = generate_voice_id()
        # Call Fish Audio API to clone voice
        fish_voice: FishVoice = await fish_client.voices.create(
            title=f"live_agent_{voice_id}",
            voices=[audio_content],
            texts=[text] if text else None,
            train_mode="fast",
            visibility="private",
            enhance_audio_quality=True
        )
        
        return fish_voice.id
    
    async def add_voice(
        self,
        db: AsyncSession,
        fish_client: AsyncFishAudio,
        owner_id: str,
        voice_id: str,
        name: str,
        desc: str,
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
            desc=desc
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
        name: str,
        desc: str
    ) -> VoiceModel:
        """
        Update voice name and/or description
        
        Args:
            db: Database session
            voice_id: Voice ID
            owner_id: User ID
            name: New voice name
            desc: New voice description
            
        Returns:
            Updated VoiceModel
        """
        # Get existing voice
        voice = await Voice.get_by_voice_and_owner(
            db=db,
            voice_id=voice_id,
            owner_id=owner_id
        )
        
        if not voice:
            from utils.exceptions import NotFoundException
            raise NotFoundException(f"Voice {voice_id} not found or not owned by user")
        
        # Update only provided fields
        new_voice = await Voice.update(
            db=db,
            voice_id=voice_id,
            owner_id=owner_id,
            name=name,
            desc=desc
        )
        
        return new_voice


voice_service = VoiceService()

