from plugins_func.register import register_function, ToolType, ActionResponse, Action
from plugins_func.functions.hass_init import initialize_hass_handler
from config.logger import setup_logging
import asyncio
import requests

TAG = __name__
logger = setup_logging()

hass_play_music_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_play_music",
        "description": "Used when user wants to listen to music or audiobooks, plays corresponding audio in the room's media player (media_player)",
        "parameters": {
            "type": "object",
            "properties": {
                "media_content_id": {
                    "type": "string",
                    "description": "Can be album name, song name, or artist name for music or audiobooks. Fill 'random' if not specified",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Device ID of the speaker to operate, entity_id in homeassistant, starts with media_player",
                },
            },
            "required": ["media_content_id", "entity_id"],
        },
    },
}


@register_function(
    "hass_play_music", hass_play_music_function_desc, ToolType.SYSTEM_CTL
)
def hass_play_music(conn, entity_id="", media_content_id="random"):
    try:
        # Execute music playback command
        future = asyncio.run_coroutine_threadsafe(
            handle_hass_play_music(
                conn, entity_id, media_content_id), conn.loop
        )
        ha_response = future.result()
        return ActionResponse(
            action=Action.RESPONSE, result="Exit intent processed", response=ha_response
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error processing music intent: {e}")


async def handle_hass_play_music(conn, entity_id, media_content_id):
    ha_config = initialize_hass_handler(conn)
    api_key = ha_config.get("api_key")
    base_url = ha_config.get("base_url")
    url = f"{base_url}/api/services/music_assistant/play_media"
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    data = {"entity_id": entity_id, "media_id": media_content_id}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return f"Now playing {media_content_id} music"
    else:
        return f"Music playback failed, error code: {response.status_code}"
