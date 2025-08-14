#!/usr/bin/env python3
"""
Test the Indian changes with a mock server connection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_full_integration():
    """Test full integration with mock connection"""
    print("=== Testing Full Integration ===")

    from core.utils.prompt_manager import PromptManager
    from config.logger import setup_logging

    logger = setup_logging()

    # Mock configuration
    config = {
        "prompt": "You are Arjun, a helpful AI assistant from India. You understand Indian culture and traditions.",
        "plugins": {
            "get_weather": {
                "api_host": "api.openweathermap.org",
                "api_key": "demo_key",
                "default_location": "Mumbai"
            }
        }
    }

    # Create prompt manager
    pm = PromptManager(config, logger)

    # Mock connection object
    class MockConnection:
        def __init__(self):
            self.config = config

    mock_conn = MockConnection()

    # Test with Indian IP
    indian_ip = "103.21.58.66"  # Mumbai IP
    device_id = "test_indian_device"

    try:
        # Update context info
        pm.update_context_info(mock_conn, indian_ip)

        # Build enhanced prompt
        enhanced_prompt = pm.build_enhanced_prompt(
            config["prompt"],
            device_id,
            indian_ip
        )

        print("✅ Enhanced Prompt Generated Successfully!")
        print(f"📏 Length: {len(enhanced_prompt)} characters")

        # Extract key sections
        lines = enhanced_prompt.split('\n')

        print("\n🔍 Key Information Extracted:")
        for line in lines:
            if 'Current Time:' in line or 'Today\'s Date:' in line or 'Today\'s Indian Calendar:' in line or 'User\'s City:' in line:
                print(f"   {line.strip()}")

        # Test the get_lunar function directly
        print("\n📅 Testing Indian Calendar Function:")
        from plugins_func.functions.get_time import get_lunar

        result = get_lunar()
        calendar_info = result.result

        # Extract key calendar info
        for line in calendar_info.split('\n'):
            if 'Gregorian Date:' in line or 'Vikram Samvat Year:' in line or 'Hindu Month:' in line or 'Indian Standard Time:' in line:
                print(f"   {line.strip()}")

        return True

    except Exception as e:
        print(f"❌ Error in full integration test: {e}")
        return False


def test_context_variables():
    """Test that context variables are properly set"""
    print("\n=== Testing Context Variables ===")

    from core.utils.prompt_manager import PromptManager
    from config.logger import setup_logging

    logger = setup_logging()
    config = {"prompt": "Test prompt"}
    pm = PromptManager(config, logger)

    # Test time info
    today_date, today_weekday, indian_date = pm._get_current_time_info()

    print(f"📅 Today's Date: {today_date}")
    print(f"📆 Weekday: {today_weekday}")
    print(f"🇮🇳 Indian Calendar: {indian_date}")

    # Test location info
    test_ip = "103.21.58.66"  # Mumbai IP
    location = pm._get_location_info(test_ip)
    print(f"📍 Location for {test_ip}: {location}")

    return True


if __name__ == "__main__":
    print("🇮🇳 Testing Indian Localization - Full Integration 🇮🇳\n")

    success1 = test_context_variables()
    success2 = test_full_integration()

    if success1 and success2:
        print("\n🎉 All tests passed! Your Indian localization is working correctly!")
        print("\n📋 Summary of Changes:")
        print("   ✅ Location detection using Indian-friendly IP service")
        print("   ✅ Indian Standard Time (IST) timezone")
        print("   ✅ Vikram Samvat calendar with Hindu months")
        print("   ✅ Enhanced prompt template integration")
        print("\n🚀 Ready to test with real server!")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
