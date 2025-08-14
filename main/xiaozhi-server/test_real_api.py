#!/usr/bin/env python3
"""
Test with the actual API key from .env file
"""

import os
import sys
import requests


def test_with_real_key():
    """Test with the API key directly from .env file"""
    print("🔑 Testing with Real API Key from .env file 🔑\n")

    # Read API key directly from .env file
    api_key = None
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('WEATHER_API='):
                    api_key = line.split('=', 1)[1].strip()
                    break
    except Exception as e:
        print(f"Error reading .env file: {e}")
        return False

    if not api_key:
        print("❌ Could not find WEATHER_API in .env file")
        return False

    print(f"📋 API Key from .env file: {api_key[:8]}...{api_key[-4:]}")

    # Test the API key
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "Mumbai",
            "appid": api_key,
            "units": "metric"
        }

        print("🧪 Testing API call to OpenWeatherMap...")
        response = requests.get(url, params=params, timeout=10)

        print(f"📊 Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            city = data["name"]
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]

            print("✅ API key is working perfectly!")
            print(f"📍 Mumbai weather: {temp}°C, {desc}")

            # Test with an Indian city
            params["q"] = "Delhi"
            response2 = requests.get(url, params=params, timeout=10)
            if response2.status_code == 200:
                data2 = response2.json()
                print(
                    f"📍 Delhi weather: {data2['main']['temp']}°C, {data2['weather'][0]['description']}")

            return True

        elif response.status_code == 401:
            print("❌ API key is invalid (401 Unauthorized)")
            print("   This might mean:")
            print("   1. The API key is incorrect")
            print("   2. The API key is not activated yet (can take a few minutes)")
            print("   3. The API key has exceeded its quota")
            return False

        elif response.status_code == 429:
            print("❌ Too many requests (429)")
            print("   You've exceeded the API rate limit")
            return False

        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False


def update_weather_function():
    """Update the weather function to use the correct API key"""
    print("\n🔧 Updating Weather Function 🔧\n")

    # Read the actual API key from .env
    api_key = None
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('WEATHER_API='):
                    api_key = line.split('=', 1)[1].strip()
                    break
    except Exception as e:
        print(f"Error reading .env file: {e}")
        return

    if not api_key:
        print("❌ Could not find API key in .env file")
        return

    print(
        f"📝 Will update weather function to use key: {api_key[:8]}...{api_key[-4:]}")

    # Update the get_openweather_api_key function to use the correct key
    try:
        with open('plugins_func/functions/get_weather.py', 'r') as f:
            content = f.read()

        # Replace the fallback key with the actual key
        old_line = 'return "your_openweathermap_api_key_here"'
        new_line = f'return "{api_key}"'

        if old_line in content:
            content = content.replace(old_line, new_line)

            with open('plugins_func/functions/get_weather.py', 'w') as f:
                f.write(content)

            print("✅ Weather function updated with your API key")
            return True
        else:
            print("❌ Could not find the line to replace in weather function")
            return False

    except Exception as e:
        print(f"❌ Error updating weather function: {e}")
        return False


if __name__ == "__main__":
    # Test the API key
    success = test_with_real_key()

    if success:
        print("\n🎉 Your API key is working!")

        # Update the weather function
        if update_weather_function():
            print("\n✅ Weather service is now ready to use!")
            print("   You can test it by running the server and asking for weather")

    else:
        print("\n❌ API key test failed.")
        print("\n🔍 Troubleshooting steps:")
        print("1. Check if your API key is correct in the .env file")
        print("2. Make sure the API key is activated (new keys take 10-15 minutes)")
        print("3. Verify you haven't exceeded your API quota")
        print("4. Try generating a new API key from OpenWeatherMap dashboard")
