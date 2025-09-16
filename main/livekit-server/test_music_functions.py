#!/usr/bin/env python3
"""
Quick test script to verify music and story function calling
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.music_service import MusicService
from services.story_service import StoryService
from services.audio_player import AudioPlayer
from agent.main_agent import Assistant

async def test_services():
    """Test the music and story services"""
    print("Testing Music and Story Services...")

    # Initialize services
    music_service = MusicService()
    story_service = StoryService()
    audio_player = AudioPlayer()

    # Test music service initialization
    print("\n1. Testing Music Service Initialization...")
    music_init = await music_service.initialize()
    print(f"Music service initialized: {music_init}")

    if music_init:
        languages = music_service.get_all_languages()
        print(f"Available music languages: {languages}")

        # Test random song
        print("\n2. Testing Random Song Selection...")
        random_song = music_service.get_random_song()
        if random_song:
            print(f"Random song: {random_song['title']} ({random_song['language']})")
            print(f"URL: {random_song['url']}")

        # Test song search
        print("\n3. Testing Song Search...")
        search_results = await music_service.search_songs("baby shark")
        if search_results:
            for result in search_results[:3]:
                print(f"Found: {result['title']} (score: {result.get('score', 'N/A')})")

    # Test story service initialization
    print("\n4. Testing Story Service Initialization...")
    story_init = await story_service.initialize()
    print(f"Story service initialized: {story_init}")

    if story_init:
        categories = story_service.get_all_categories()
        print(f"Available story categories: {categories}")

        # Test random story
        print("\n5. Testing Random Story Selection...")
        random_story = story_service.get_random_story()
        if random_story:
            print(f"Random story: {random_story['title']} ({random_story['category']})")
            print(f"URL: {random_story['url']}")

        # Test story search
        print("\n6. Testing Story Search...")
        search_results = await story_service.search_stories("bertie")
        if search_results:
            for result in search_results[:3]:
                print(f"Found: {result['title']} (score: {result.get('score', 'N/A')})")

    # Test agent function tools (simulation)
    print("\n7. Testing Agent Function Tools...")
    assistant = Assistant()
    assistant.set_services(music_service, story_service, audio_player)

    # Test with mock context
    class MockContext:
        pass

    mock_context = MockContext()

    # Test play_music function
    if music_init:
        print("\nTesting play_music function...")
        result = await assistant.play_music(mock_context)
        print(f"Random music result: {result}")

        result = await assistant.play_music(mock_context, song_name="baby shark")
        print(f"Specific song result: {result}")

    # Test play_story function
    if story_init:
        print("\nTesting play_story function...")
        result = await assistant.play_story(mock_context)
        print(f"Random story result: {result}")

        result = await assistant.play_story(mock_context, story_name="bertie")
        print(f"Specific story result: {result}")

if __name__ == "__main__":
    asyncio.run(test_services())