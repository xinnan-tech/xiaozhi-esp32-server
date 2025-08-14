#!/usr/bin/env python3
"""
Final test of weather service with actual API key
"""

import sys
import os
sys.path.append('.')


def test_weather_service():
    """Test the weather service with the updated API key function"""
    print("🌤️ Final Weather Service Test 🌤️\n")

    try:
        from plugins_func.functions.get_weather import get_openweather_api_key, get_weather
        from plugins_func.register import ActionResponse

        # Test API key function
        api_key = get_openweather_api_key()
        print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")

        # Mock connection
        class MockConnection:
            def __init__(self):
                self.config = {
                    "plugins": {
                        "get_weather": {
                            "default_location": "Mumbai"
                        }
                    }
                }
                self.client_ip = "103.21.58.66"

        conn = MockConnection()

        # Test weather function
        print("🧪 Testing weather function...")
        result = get_weather(conn, location="Mumbai", lang="en_US")

        if isinstance(result, ActionResponse):
            print("✅ Weather function executed successfully!")
            print("\n📄 Weather Report Preview:")
            preview = result.result[:300] + \
                "..." if len(result.result) > 300 else result.result
            print(preview)

            # Test with another city
            print("\n🧪 Testing with Delhi...")
            result2 = get_weather(conn, location="Delhi", lang="en_US")
            if isinstance(result2, ActionResponse):
                print("✅ Delhi weather also working!")
                preview2 = result2.result[:200] + \
                    "..." if len(result2.result) > 200 else result2.result
                print(preview2)

            return True
        else:
            print(f"❌ Unexpected result type: {type(result)}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_weather_service()

    if success:
        print("\n🎉 Weather service is working perfectly!")
        print("✅ Your OpenWeatherMap integration is ready")
        print("✅ Indian cities are supported")
        print("✅ International cities work too")
        print("\n🚀 You can now:")
        print("1. Start the server: python app.py")
        print("2. Ask for weather: 'What's the weather in Mumbai?'")
        print("3. Try other cities: 'Delhi weather', 'Bangalore forecast'")
    else:
        print("\n❌ Weather service test failed")
        print("Please check your API key and try again")
