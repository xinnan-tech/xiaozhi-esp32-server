from plugins_func.register import register_function, ToolType, ActionResponse, Action
from plugins_func.functions.hass_init import initialize_hass_handler
from config.logger import setup_logging
import asyncio
import requests

TAG = __name__
logger = setup_logging()

hass_get_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_get_state",
        "description": "Get device status in homeassistant, including querying light brightness, color, color temperature, media player volume, device pause/resume operations",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Device ID to operate, entity_id in homeassistant",
                },
            },
            "required": ["entity_id"],
        },
    },
}


@register_function("hass_get_state", hass_get_state_function_desc, ToolType.SYSTEM_CTL)
def hass_get_state(conn, entity_id=""):
    try:
        future = asyncio.run_coroutine_threadsafe(
            handle_hass_get_state(conn, entity_id), conn.loop
        )
        ha_response = future.result()
        return ActionResponse(Action.REQLLM, ha_response, None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error processing get state intent: {e}")


async def handle_hass_get_state(conn, entity_id):
    ha_config = initialize_hass_handler(conn)
    api_key = ha_config.get("api_key")
    base_url = ha_config.get("base_url")
    url = f"{base_url}/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        responsetext = "Device status: " + response.json()["state"] + " "
        logger.bind(tag=TAG).info(f"API return content: {response.json()}")

        if "media_title" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "Currently playing: "
                + str(response.json()["attributes"]["media_title"])
                + " "
            )

        if "volume_level" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "Volume is: "
                + str(response.json()["attributes"]["volume_level"])
                + " "
            )

        if "color_temp_kelvin" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "Color temperature is: "
                + str(response.json()["attributes"]["color_temp_kelvin"])
                + " "
            )

        if "rgb_color" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "RGB color is: "
                + str(response.json()["attributes"]["rgb_color"])
                + " "
            )

        if "brightness" in response.json()["attributes"]:
            responsetext = (
                responsetext
                + "Brightness is: "
                + str(response.json()["attributes"]["brightness"])
                + " "
            )

        logger.bind(tag=TAG).info(f"Query return content: {responsetext}")
        return responsetext
        # return response.json()['attributes']
        # response.attributes
    else:
        return f"Switch failed, error code: {response.status_code}"
