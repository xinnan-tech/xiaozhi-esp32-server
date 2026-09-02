import os
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info, fetch_lat_lon

TAG = "plugins_func.functions.get_location"
logger = setup_logging()

GET_LOCATION_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_location",
        "description": "Get the current location of the device.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

@register_function("get_location", GET_LOCATION_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_location(conn):
    try:
        # 1. Try IP Geolocation First (Automatic identification)
        ip_info = get_ip_info(conn.client_ip, logger)
        if ip_info and ip_info.get("city"):
             city = ip_info.get("city")
             region = ip_info.get("region")
             country = ip_info.get("country")
             loc_str = f"{city}, {region}, {country}"
             response = f"I detected you are in {loc_str} (based on IP address)."
             logger.bind(tag=TAG).info(f"Location resolved via IP: {loc_str}")
             return ActionResponse(Action.REQLLM, response, None)

        logger.bind(tag=TAG).info("IP location failed, checking client config...")

        # 2. Check Client Config (Fallback)
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

        location_source = "Client Config"
        if not client_location:
            # 3. Check Global Config (Last resort)
            from config.config_loader import load_config
            cfg = load_config()
            client_location = cfg.get("plugins", {}).get("get_weather", {}).get("default_location")
            location_source = "Global Config"
            
        if client_location:
            lat, lon, resolved_name = fetch_lat_lon(client_location)
            if resolved_name:
                response = f"You are currently in {resolved_name} (set via {location_source})."
                logger.bind(tag=TAG).info(f"Location resolved via {location_source}: {resolved_name}")
                return ActionResponse(Action.REQLLM, response, None)
            else:
                 logger.bind(tag=TAG).warning(f"Failed to geocode location '{client_location}' from {location_source}")

        return ActionResponse(Action.REQLLM, "I couldn't determine your location.", None)
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting location: {e}")
        return ActionResponse(Action.REQLLM, "An error occurred while checking location.", None)
