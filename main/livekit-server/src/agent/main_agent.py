import logging
from typing import Optional
from livekit.agents import (
    Agent,
    RunContext,
    function_tool,
)

logger = logging.getLogger("agent")

class Assistant(Agent):
    """Main AI Assistant agent class"""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.

            You can play music and stories for users. When users ask to play music, sing a song, or play a story,
            you can search for specific content or play random content from available collections.""",
        )

        # These will be injected by main.py
        self.music_service = None
        self.story_service = None
        self.audio_player = None

    def set_services(self, music_service, story_service, audio_player):
        """Set the music and story services"""
        self.music_service = music_service
        self.story_service = story_service
        self.audio_player = audio_player

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str):
        """Look up weather information for a specific location"""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

    @function_tool
    async def play_music(
        self,
        context: RunContext,
        song_name: Optional[str] = None,
        language: Optional[str] = None
    ):
        """Play music - either a specific song or random music

        Args:
            song_name: Optional specific song to search for
            language: Optional language preference (English, Hindi, Telugu, etc.)
        """
        try:
            logger.info(f"Music request - song: '{song_name}', language: '{language}'")

            if not self.music_service or not self.audio_player:
                return "Sorry, music service is not available right now."

            if song_name:
                # Search for specific song
                songs = await self.music_service.search_songs(song_name, language)
                if songs:
                    song = songs[0]  # Take first match
                    logger.info(f"Found song: {song['title']} in {song['language']}")
                else:
                    logger.info(f"No songs found for '{song_name}', playing random song")
                    song = self.music_service.get_random_song(language)
            else:
                # Play random song
                song = self.music_service.get_random_song(language)

            if not song:
                return "Sorry, I couldn't find any music to play right now."

            # Start playing the song
            await self.audio_player.play_from_url(song['url'], song['title'])

            return f"Now playing: {song['title']}"

        except Exception as e:
            logger.error(f"Error playing music: {e}")
            return "Sorry, I encountered an error while trying to play music."

    @function_tool
    async def play_story(
        self,
        context: RunContext,
        story_name: Optional[str] = None,
        category: Optional[str] = None
    ):
        """Play a story - either a specific story or random story

        Args:
            story_name: Optional specific story to search for
            category: Optional category preference (Adventure, Bedtime, Educational, etc.)
        """
        try:
            logger.info(f"Story request - story: '{story_name}', category: '{category}'")

            if not self.story_service or not self.audio_player:
                return "Sorry, story service is not available right now."

            if story_name:
                # Search for specific story
                stories = await self.story_service.search_stories(story_name, category)
                if stories:
                    story = stories[0]  # Take first match
                    logger.info(f"Found story: {story['title']} in {story['category']}")
                else:
                    logger.info(f"No stories found for '{story_name}', playing random story")
                    story = self.story_service.get_random_story(category)
            else:
                # Play random story
                story = self.story_service.get_random_story(category)

            if not story:
                return "Sorry, I couldn't find any stories to play right now."

            # Start playing the story
            await self.audio_player.play_from_url(story['url'], story['title'])

            return f"Now playing story: {story['title']}"

        except Exception as e:
            logger.error(f"Error playing story: {e}")
            return "Sorry, I encountered an error while trying to play the story."

    @function_tool
    async def stop_audio(self, context: RunContext):
        """Stop any currently playing audio (music or story)"""
        try:
            if self.audio_player:
                await self.audio_player.stop()
                return "Stopped playing audio."
            else:
                return "No audio is currently playing."
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")
            return "Sorry, I encountered an error while trying to stop audio."