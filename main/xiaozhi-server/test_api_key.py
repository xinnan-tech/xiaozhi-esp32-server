#!/usr/bin/env python3
"""
Test OpenWeatherMap API key
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def test_api_key():
    """Test if the OpenWeatherMap API key is working"""
    print("🔑 Testing OpenWeatherMap API Key 🔑\n")

    # Get API key from environment
    api_key = os.getenv('WEATHER_API')

    print(f"API Key from environment: {api_key}")

    if not api_key or api_key == "your_actual_api_key_here":
        print("❌ API key not set properly")
        return False

    # Test the API key with a simple request
    print(f"🧪 Testing API key: {api_key[:8]}...{api_key[-4:]}")

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "Mumbai",
            "appid": api_key,
            "units": "metric"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            city = data["name"]
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]

            print("✅ API key is working!")
            print(f"📍 Test result: {city} - {temp}°C, {desc}")
            return True

        elif response.status_code == 401:
            print("❌ API key is invalid (401 Unauthorized)")
            print("   Please check your OpenWeatherMap API key")
            return False

        else:
            print(
                f"❌ API request failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False


def test_env_loading():
    """Test environment variable loading"""
    print("\n🔧 Testing Environment Variable Loading 🔧\n")

    # Test direct environment access
    direct_key = os.getenv('WEATHER_API')
    print(f"Direct os.getenv('WEATHER_API'): {direct_key}")

    # Test with dotenv
    load_dotenv()
    dotenv_key = os.getenv('WEATHER_API')
    print(f"After load_dotenv(): {dotenv_key}")

    # Check .env file content
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
            print(f"\n.env file content:")
            for line in env_content.split('\n'):
                if 'WEATHER_API' in line:
                    print(f"  {line}")
    except Exception as e:
        print(f"Error reading .env file: {e}")


if __name__ == "__main__":
    test_env_loading()
    success = test_api_key()

    if success:
        print("\n🎉 Your OpenWeatherMap API key is working correctly!")
        print("   The weather service should work now.")
    else:
        print("\n❌ API key test failed.")
        print("   Please check:")
        print("   1. Your API key is correct")
        print("   2. The API key is active (new keys may take a few minutes)")
        print("   3. You have API calls remaining in your quota")
