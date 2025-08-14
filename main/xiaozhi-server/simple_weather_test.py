import os
import sys
sys.path.append('.')

# Set API key for testing
os.environ['WEATHER_API'] = 'demo_key_for_testing'

print("Testing weather service...")

try:
    from plugins_func.functions.get_weather import normalize_indian_city_name, get_openweather_api_key

    print("✅ Weather module imported successfully")

    # Test city normalization
    test_cities = ["bombay", "bangalore", "delhi"]
    print("\nCity normalization test:")
    for city in test_cities:
        normalized = normalize_indian_city_name(city)
        print(f"  {city} -> {normalized}")

    # Test API key function
    api_key = get_openweather_api_key()
    print(f"\nAPI key function: {api_key}")

    print("\n✅ All basic tests passed!")
    print("\n📝 To use with real API:")
    print("1. Get your free API key from: https://openweathermap.org/api")
    print("2. Set environment variable: WEATHER_API=your_actual_key")
    print("3. Update .env file with your key")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
