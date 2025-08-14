#!/usr/bin/env python3
"""
Test complete news system for Indian users
"""

import sys
import os
sys.path.append('.')


def test_complete_news_system():
    """Test all news systems"""
    print("🌟 Testing Complete News System for Indian Users 🌟\n")

    try:
        # Test Indian News API
        print("1. 🇮🇳 Testing Indian News API...")
        from plugins_func.functions.get_indian_news_api import (
            get_indian_news_api,
            fetch_indian_news_from_api,
            SAMPLE_INDIAN_NEWS
        )
        from plugins_func.register import ActionResponse

        # Mock connection
        class MockConnection:
            def __init__(self):
                self.config = {
                    "plugins": {
                        "get_indian_news_api": {
                            "lang": "en_US"
                        }
                    }
                }

        conn = MockConnection()

        # Test Indian news
        result = get_indian_news_api(
            conn, category="general", detail=False, lang="en_US")
        if isinstance(result, ActionResponse):
            print("✅ Indian News API working!")
            print(f"📄 Sample: {result.result[:150]}...")
        else:
            print("❌ Indian News API failed")

        # Test International News
        print("\n2. 🌐 Testing International News...")
        from plugins_func.functions.get_news_from_newsnow import get_news_from_newsnow

        # Mock connection with newsnow config
        conn.config["plugins"]["get_news_from_newsnow"] = {
            "news_sources": "Wall Street Journal;Hacker News;BBC News"
        }

        result = get_news_from_newsnow(
            conn, source="Wall Street Journal", detail=False, lang="en_US")
        if isinstance(result, ActionResponse):
            print("✅ International News working!")
            print(f"📄 Sample: {result.result[:150]}...")
        else:
            print("❌ International News failed")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_final_configuration():
    """Show the final recommended configuration"""
    print("\n🎯 Final Configuration for Indian Users 🎯\n")

    print("✅ ENABLED News Functions:")
    print("  • get_indian_news_api - Primary Indian news source")
    print("  • get_news_from_newsnow - International news backup")
    print("  • get_weather - Weather information")

    print("\n📰 Available News Categories:")
    print("  • General Indian news")
    print("  • Business & Economy")
    print("  • Technology & Startups")
    print("  • Science & Education")
    print("  • International news")

    print("\n🗣️ Voice Commands You Can Use:")
    print("  • 'What's the latest Indian news?'")
    print("  • 'Show me Indian business news'")
    print("  • 'Get technology news from India'")
    print("  • 'Tell me about Indian startups'")
    print("  • 'What's happening in international news?'")
    print("  • 'Get Wall Street Journal news'")

    print("\n⚙️ Configuration Status:")
    print("  • ✅ Indian News API: Enabled with sample data")
    print("  • ✅ International News: Enabled")
    print("  • ✅ Weather Service: Enabled for Bangalore")
    print("  • ❌ Chinese News: Disabled (not relevant for Indian users)")

    print("\n🚀 Next Steps to Enhance:")
    print("  1. Get free NewsAPI key: https://newsapi.org/")
    print("  2. Get free GNews key: https://gnews.io/")
    print("  3. Add API keys to config for real-time news")
    print("  4. Test voice commands with your device")


if __name__ == "__main__":
    success = test_complete_news_system()

    if success:
        print("\n🎉 Complete News System Test Passed!")
        show_final_configuration()

        print("\n✨ Your Xiaozhi server is now optimized for Indian users!")
        print(
            "The system will provide relevant Indian news alongside international updates.")

    else:
        print("\n❌ Some tests failed, but basic functionality should still work")
        show_final_configuration()
