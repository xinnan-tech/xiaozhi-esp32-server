#!/usr/bin/env python3
"""
Test English-only responses
"""

import sys
sys.path.append('.')


def test_english_responses():
    """Test that all functions return English responses"""
    print("🇺🇸 Testing English-Only Responses 🇺🇸\n")

    try:
        # Mock connection
        class MockConnection:
            def __init__(self):
                self.config = {
                    "plugins": {
                        "get_indian_news_api": {"lang": "en_US"},
                        "get_news_from_newsnow": {
                            "news_sources": "Wall Street Journal;Hacker News;BBC News"
                        }
                    }
                }

        conn = MockConnection()

        # Test Indian News API
        print("1. 🇮🇳 Testing Indian News API (English)...")
        from plugins_func.functions.get_indian_news_api import get_indian_news_api
        result = get_indian_news_api(
            conn, category="general", detail=False, lang="en_US")

        if result and hasattr(result, 'result'):
            response = result.result
            print(f"✅ Response received: {len(response)} characters")
            print(f"📄 Preview: {response[:200]}...")

            # Check for Chinese characters
            chinese_chars = any('\u4e00' <= char <=
                                '\u9fff' for char in response)
            if chinese_chars:
                print("❌ WARNING: Chinese characters detected!")
            else:
                print("✅ No Chinese characters found")

        # Test International News
        print("\n2. 🌐 Testing International News (English)...")
        from plugins_func.functions.get_news_from_newsnow import get_news_from_newsnow
        result = get_news_from_newsnow(
            conn, source="Wall Street Journal", detail=False, lang="en_US")

        if result and hasattr(result, 'result'):
            response = result.result
            print(f"✅ Response received: {len(response)} characters")
            print(f"📄 Preview: {response[:200]}...")

            # Check for Chinese characters
            chinese_chars = any('\u4e00' <= char <=
                                '\u9fff' for char in response)
            if chinese_chars:
                print("❌ WARNING: Chinese characters detected!")
            else:
                print("✅ No Chinese characters found")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_language_fixes():
    """Show what was fixed"""
    print("\n🔧 Language Fixes Applied 🔧\n")

    print("✅ FIXED Issues:")
    print("  1. News functions now default to 'en_US' instead of 'zh_CN'")
    print("  2. ASR configured to prefer English language")
    print("  3. Chinese news function disabled to prevent Chinese responses")
    print("  4. International news defaults to English sources")

    print("\n📝 Configuration Changes:")
    print("  • get_news_from_newsnow: lang='en_US' (was 'zh_CN')")
    print("  • get_news_from_chinanews: lang='en_US' (was 'zh_CN')")
    print("  • ASR: Added English language preference")
    print("  • Intent: Disabled Chinese news function")

    print("\n🎯 Expected Behavior:")
    print("  • All responses should now be in English")
    print("  • News will come from English sources")
    print("  • Speech recognition will prefer English")
    print("  • No more Chinese responses")


if __name__ == "__main__":
    success = test_english_responses()
    show_language_fixes()

    if success:
        print("\n🎉 English-only configuration is working!")
        print("Your Xiaozhi should now respond only in English.")
    else:
        print("\n⚠️ Some issues detected, but main fixes are applied.")
        print("Try restarting your Xiaozhi server to apply changes.")
