import requests
import os
from datetime import datetime, timedelta
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get weather for a location, user should provide a location, e.g., if user says 'Mumbai weather', parameter is: Mumbai. "
            "If user mentions a state, defaults to state capital. If user mentions a place name that's not a state or city, defaults to the nearest major city. "
            "If user doesn't specify location, saying 'how's the weather', 'how's today's weather', location parameter is empty. "
            "Supports Indian cities and international locations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location name, e.g., Mumbai, Delhi, Bangalore. Optional parameter, don't pass if not provided",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for user response, e.g., en_US/hi_IN/zh_CN etc., defaults to en_US",
                },
            },
            "required": ["lang"],
        },
    },
}

# Indian city name mappings for better recognition
INDIAN_CITY_MAPPINGS = {
    "bombay": "Mumbai",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "bangalore": "Bengaluru",
    "poona": "Pune",
    "delhi": "New Delhi",
    "hyderabad": "Hyderabad",
    "ahmedabad": "Ahmedabad",
    "chennai": "Chennai",
    "kolkata": "Kolkata",
    "surat": "Surat",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
    "kanpur": "Kanpur",
    "nagpur": "Nagpur",
    "indore": "Indore",
    "thane": "Thane",
    "bhopal": "Bhopal",
    "visakhapatnam": "Visakhapatnam",
    "pimpri": "Pimpri-Chinchwad",
    "patna": "Patna",
    "vadodara": "Vadodara",
    "ghaziabad": "Ghaziabad",
    "ludhiana": "Ludhiana",
    "agra": "Agra",
    "nashik": "Nashik",
    "faridabad": "Faridabad",
    "meerut": "Meerut",
    "rajkot": "Rajkot",
    "kalyan": "Kalyan-Dombivli",
    "vasai": "Vasai-Virar",
    "varanasi": "Varanasi",
    "srinagar": "Srinagar",
    "aurangabad": "Aurangabad",
    "dhanbad": "Dhanbad",
    "amritsar": "Amritsar",
    "navi mumbai": "Navi Mumbai",
    "allahabad": "Prayagraj",
    "ranchi": "Ranchi",
    "howrah": "Howrah",
    "coimbatore": "Coimbatore",
    "jabalpur": "Jabalpur",
    "gwalior": "Gwalior",
    "vijayawada": "Vijayawada",
    "jodhpur": "Jodhpur",
    "madurai": "Madurai",
    "raipur": "Raipur",
    "kota": "Kota",
    "chandigarh": "Chandigarh",
    "guwahati": "Guwahati",
    "solapur": "Solapur",
    "hubli": "Hubballi-Dharwad",
    "tiruchirappalli": "Tiruchirappalli",
    "bareilly": "Bareilly",
    "mysore": "Mysuru",
    "tiruppur": "Tiruppur",
    "gurgaon": "Gurugram",
    "aligarh": "Aligarh",
    "jalandhar": "Jalandhar",
    "bhubaneswar": "Bhubaneswar",
    "salem": "Salem",
    "warangal": "Warangal",
    "mira": "Mira-Bhayandar",
    "thiruvananthapuram": "Thiruvananthapuram",
    "bhiwandi": "Bhiwandi",
    "saharanpur": "Saharanpur",
    "guntur": "Guntur",
    "amravati": "Amravati",
    "bikaner": "Bikaner",
    "noida": "Noida",
    "jamshedpur": "Jamshedpur",
    "bhilai": "Bhilai Nagar",
    "cuttack": "Cuttack",
    "firozabad": "Firozabad",
    "kochi": "Kochi",
    "bhavnagar": "Bhavnagar",
    "dehradun": "Dehradun",
    "durgapur": "Durgapur",
    "asansol": "Asansol",
    "nanded": "Nanded-Waghala",
    "kolhapur": "Kolhapur",
    "ajmer": "Ajmer",
    "gulbarga": "Kalaburagi",
    "jamnagar": "Jamnagar",
    "ujjain": "Ujjain",
    "loni": "Loni",
    "siliguri": "Siliguri",
    "jhansi": "Jhansi",
    "ulhasnagar": "Ulhasnagar",
    "nellore": "Nellore",
    "jammu": "Jammu",
    "sangli": "Sangli-Miraj & Kupwad",
    "belgaum": "Belagavi",
    "mangalore": "Mangaluru",
    "ambattur": "Ambattur",
    "tirunelveli": "Tirunelveli",
    "malegaon": "Malegaon",
    "gaya": "Gaya",
    "jalgaon": "Jalgaon",
    "udaipur": "Udaipur",
    "maheshtala": "Maheshtala"
}


def normalize_indian_city_name(city_name):
    """Normalize Indian city names for better API recognition"""
    if not city_name:
        return city_name

    city_lower = city_name.lower().strip()

    # Check if it's in our mapping
    if city_lower in INDIAN_CITY_MAPPINGS:
        return INDIAN_CITY_MAPPINGS[city_lower]

    # Return original with proper capitalization
    return city_name.title()


def get_openweather_api_key():
    """Get OpenWeatherMap API key from environment or config"""
    # First try environment variable (but skip if it's the demo key)
    api_key = os.getenv('WEATHER_API')
    if api_key and api_key != 'demo_key' and api_key != 'demo_key_for_testing':
        return api_key

    # Try to read from .env file directly
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('WEATHER_API='):
                    env_key = line.split('=', 1)[1].strip()
                    if env_key and env_key != 'your_actual_api_key_here':
                        return env_key
    except:
        pass

    # Use your actual API key as fallback
    return "12dd0eea5789636262549c9ec7f4f7d8"


def fetch_current_weather(location, api_key, lang="en"):
    """Fetch current weather from OpenWeatherMap"""
    try:
        # Normalize city name for Indian cities
        normalized_location = normalize_indian_city_name(location)

        # Current weather API
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": normalized_location,
            "appid": api_key,
            "units": "metric",  # Celsius
            "lang": lang
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error fetching current weather: {e}")
        return None


def fetch_forecast_weather(location, api_key, lang="en"):
    """Fetch 5-day weather forecast from OpenWeatherMap"""
    try:
        # Normalize city name for Indian cities
        normalized_location = normalize_indian_city_name(location)

        # 5-day forecast API
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": normalized_location,
            "appid": api_key,
            "units": "metric",  # Celsius
            "lang": lang
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json()
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error fetching forecast weather: {e}")
        return None


def format_weather_report(current_data, forecast_data, lang="en"):
    """Format weather data into a readable report"""
    if not current_data:
        return "Unable to fetch weather data"

    try:
        # Current weather info
        city_name = current_data["name"]
        country = current_data["sys"]["country"]

        # Current conditions
        temp = round(current_data["main"]["temp"])
        feels_like = round(current_data["main"]["feels_like"])
        humidity = current_data["main"]["humidity"]
        pressure = current_data["main"]["pressure"]

        weather_desc = current_data["weather"][0]["description"].title()

        # Wind info
        wind_speed = current_data.get("wind", {}).get("speed", 0)
        wind_speed_kmh = round(wind_speed * 3.6)  # Convert m/s to km/h

        # Visibility
        visibility = current_data.get("visibility", 0) / 1000  # Convert to km

        # Sunrise/Sunset (convert from UTC to local time)
        sunrise = datetime.fromtimestamp(current_data["sys"]["sunrise"])
        sunset = datetime.fromtimestamp(current_data["sys"]["sunset"])

        # Build current weather report
        report = f"📍 Weather for {city_name}, {country}\n\n"
        report += f"🌡️ Current Temperature: {temp}°C (feels like {feels_like}°C)\n"
        report += f"☁️ Conditions: {weather_desc}\n"
        report += f"💧 Humidity: {humidity}%\n"
        report += f"🌬️ Wind Speed: {wind_speed_kmh} km/h\n"
        report += f"📊 Pressure: {pressure} hPa\n"

        if visibility > 0:
            report += f"👁️ Visibility: {visibility:.1f} km\n"

        report += f"🌅 Sunrise: {sunrise.strftime('%I:%M %p')}\n"
        report += f"🌇 Sunset: {sunset.strftime('%I:%M %p')}\n"

        # Add forecast if available
        if forecast_data and "list" in forecast_data:
            report += "\n📅 5-Day Forecast:\n"

            # Group forecast by day
            daily_forecasts = {}
            for item in forecast_data["list"]:
                date = datetime.fromtimestamp(item["dt"]).date()
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                daily_forecasts[date].append(item)

            # Show next 5 days
            count = 0
            for date, forecasts in daily_forecasts.items():
                if count >= 5:
                    break

                # Get min/max temps for the day
                temps = [f["main"]["temp"] for f in forecasts]
                min_temp = round(min(temps))
                max_temp = round(max(temps))

                # Get most common weather condition
                conditions = [f["weather"][0]["description"]
                              for f in forecasts]
                most_common_condition = max(
                    set(conditions), key=conditions.count).title()

                day_name = date.strftime("%A")
                date_str = date.strftime("%d %b")

                report += f"  {day_name} ({date_str}): {most_common_condition}, {min_temp}°C - {max_temp}°C\n"
                count += 1

        report += "\n💡 Tip: Ask me about weather for specific dates or other cities!"

        return report

    except Exception as e:
        logger.bind(tag=TAG).error(f"Error formatting weather report: {e}")
        return f"Weather data received but formatting failed: {str(e)}"


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_weather(conn, location: str = None, lang: str = "en_US"):
    from core.utils.cache.manager import cache_manager, CacheType

    # Get OpenWeatherMap API key
    api_key = get_openweather_api_key()

    # Check if API key is properly configured
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return ActionResponse(
            Action.REQLLM,
            "Weather service not configured. Please set your OpenWeatherMap API key in the WEATHER_API environment variable.",
            None
        )

    # Get default location from config
    default_location = conn.config.get("plugins", {}).get(
        "get_weather", {}).get("default_location", "Mumbai")
    client_ip = getattr(conn, 'client_ip', None)

    # Determine location to query
    if not location:
        # Parse city through client IP
        if client_ip:
            # First get IP corresponding city info from cache
            cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
            if cached_ip_info:
                location = cached_ip_info.get("city", "").split(",")[
                    0]  # Get city name only
            else:
                # Cache miss, call API to get
                ip_info = get_ip_info(client_ip, logger)
                if ip_info:
                    cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
                    location = ip_info.get("city", "").split(",")[
                        0]  # Get city name only

            if not location:
                location = default_location
        else:
            # If no IP, use default location
            location = default_location

    # Clean up location name (remove state/country info if present)
    if "," in location:
        location = location.split(",")[0].strip()

    # Try to get complete weather report from cache (cache for 10 minutes)
    weather_cache_key = f"openweather_{location}_{lang}"
    cached_weather_report = cache_manager.get(
        CacheType.WEATHER, weather_cache_key)

    if cached_weather_report:
        logger.bind(tag=TAG).info(f"Using cached weather data for {location}")
        return ActionResponse(Action.REQLLM, cached_weather_report, None)

    # Cache miss, get real-time weather data
    logger.bind(tag=TAG).info(f"Fetching weather data for {location}")

    # Convert language code
    api_lang = "en"
    if lang.startswith("hi"):
        api_lang = "hi"
    elif lang.startswith("zh"):
        api_lang = "zh_cn"

    # Fetch current weather and forecast
    current_data = fetch_current_weather(location, api_key, api_lang)
    forecast_data = fetch_forecast_weather(location, api_key, api_lang)

    if not current_data:
        return ActionResponse(
            Action.REQLLM,
            f"Unable to find weather data for '{location}'. Please check the city name and try again. "
            f"For Indian cities, try using the English name (e.g., 'Mumbai' instead of 'Bombay').",
            None
        )

    # Format the weather report
    weather_report = format_weather_report(current_data, forecast_data, lang)

    # Cache the weather report (10 minutes TTL)
    cache_manager.set(CacheType.WEATHER, weather_cache_key,
                      weather_report, ttl=600)

    logger.bind(tag=TAG).info(
        f"Weather data fetched and cached for {location}")
    return ActionResponse(Action.REQLLM, weather_report, None)
