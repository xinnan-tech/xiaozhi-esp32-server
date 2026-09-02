import requests
from config.logger import setup_logging
from config.config_loader import load_config
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info, fetch_lat_lon

TAG = "plugins_func.functions.get_weather"
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get the weather for a specific location. The user should provide a location, "
            "e.g., if the user says 'Weather in Raleigh', the parameter is 'Raleigh'. "
            "If the user does not specify a location (e.g., 'How is the weather?'), "
            "the location parameter will be empty and the system will use the device location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The name of the location, e.g., Raleigh. Optional.",
                },
            },
        },
    },
}

# WMO Weather Codes (Open-Meteo)
# https://open-meteo.com/en/docs
WMO_CODES = {
    0: "clear skies",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "a thunderstorm",
    96: "a thunderstorm with slight hail",
    99: "a thunderstorm with heavy hail"
}

def fetch_weather_from_open_meteo(lat, lon, unit_system="metric"):
    """
    Fetch weather from Open-Meteo API (Free, No Key).
    """
    # Base URL with current and daily forecast parameters
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
        "&timezone=auto"
    )
    
    # Add unit parameters if imperial
    if unit_system == "imperial":
        url += "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
    else:
        url += "&wind_speed_unit=ms"
    
    try:
        logger.bind(tag=TAG).info(f"Requesting Open-Meteo Weather: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("current"), data.get("daily"), data.get("current_units"), data.get("daily_units")
        else:
            logger.bind(tag=TAG).error(f"Open-Meteo API Error {response.status_code}: {response.text}")
            return None, None, None, None
    except Exception as e:
        logger.bind(tag=TAG).error(f"Open-Meteo API failed: {e}")
        return None, None, None, None

@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_weather(conn, location: str = None, lang: str = "en_US"):
    
    lat = None
    lon = None
    place_name = location

    # 0. Load Configuration
    config = load_config()
    weather_config = config.get("plugins", {}).get("get_weather", {})
    unit_system = weather_config.get("unit_system", "metric")

    # 1. Determine Location (Lat/Lon)
    if location:
        # Resolve user-provided location
        lat, lon, resolved_name = fetch_lat_lon(location)
        if resolved_name:
            place_name = resolved_name
        else:
             return ActionResponse(Action.REQLLM, f"I couldn't find the location '{location}'.", None)
    else:
        # No location provided, find default
        
        # 1. Try IP Geolocation First (Automatic)
        ip_info = get_ip_info(conn.client_ip, logger)
        if ip_info and ip_info.get("lat") and ip_info.get("lon"):
            lat = ip_info["lat"]
            lon = ip_info["lon"]
            city = ip_info.get("city", "your location")
            place_name = city
            logger.bind(tag=TAG).info(f"Resolved IP to {city} ({lat}, {lon})")
        else:
             logger.bind(tag=TAG).info("IP location failed or unreliable, checking client config fallback")

        # 2. Check Client Config (Fallback)
        if not lat or not lon:
            client_location = None
            if hasattr(conn, "client_id") and conn.client_id:
                 client_config_path = os.path.join("data", conn.client_id, "config.json")
                 if os.path.exists(client_config_path):
                     try:
                         with open(client_config_path, "r", encoding="utf-8") as f:
                             c = json.load(f)
                             client_location = c.get("default_location") or c.get("location")
                     except Exception as e:
                         logger.bind(tag=TAG).warning(f"Failed to read client config: {e}")

            if client_location:
                lat, lon, resolved_name = fetch_lat_lon(client_location)
                if resolved_name:
                    place_name = resolved_name
                    logger.bind(tag=TAG).info(f"Using client fallback location: {resolved_name}")
                else:
                     logger.bind(tag=TAG).warning(f"Failed to resolve client fallback location: {client_location}")
        
        # 3. Fallback to Global Configured Default
        if not lat or not lon:
             default_loc = weather_config.get("default_location", "Raleigh")
             logger.bind(tag=TAG).info(f"Location lookup failed, falling back to global default: {default_loc}")
             lat, lon, resolved_name = fetch_lat_lon(default_loc)
             place_name = resolved_name or default_loc


    if not lat or not lon:
        return ActionResponse(Action.REQLLM, "I couldn't determine the location to check the weather.", None)

    # 2. Fetch Weather from Open-Meteo
    current, daily, c_units, d_units = fetch_weather_from_open_meteo(lat, lon, unit_system)
    
    if not current:
        return ActionResponse(Action.REQLLM, f"I couldn't retrieve the weather for {place_name} at the moment.", None)
        
    # 3. Format Response
    temp = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind_speed = current.get("wind_speed_10m")
    
    # Current condition
    code = current.get("weather_code")
    condition = WMO_CODES.get(code, "unknown")
    
    # Daily forecast (today)
    forecast_str = ""
    if daily and daily.get("temperature_2m_max"):
        t_max = daily["temperature_2m_max"][0]
        t_min = daily["temperature_2m_min"][0]
        precip_prob = daily["precipitation_probability_max"][0]
        d_code = daily["weather_code"][0]
        d_condition = WMO_CODES.get(d_code, condition)
        
        forecast_str = (
            f"Today's forecast is {d_condition} with a high of {t_max}{c_units.get('temperature_2m', '°C')} "
            f"and a low of {t_min}{c_units.get('temperature_2m', '°C')}. "
            f"There's a {precip_prob}% chance of rain."
        )

    weather_report = (
        f"In {place_name}, it is currently {condition}. "
        f"The temperature is {temp}{c_units.get('temperature_2m', '°C')} (feels like {feels_like}{c_units.get('temperature_2m', '°C')}). "
        f"{forecast_str}"
    )
    
    return ActionResponse(Action.REQLLM, weather_report, None)
