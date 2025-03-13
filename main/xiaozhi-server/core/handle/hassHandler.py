import requests
from config.logger import setup_logging


class HassHandler:
    def __init__(self, config):
        self.config = config
        self.base_url = config["LLM"]['HomeAssistant']['base_url']
        self.api_key = config["LLM"]['HomeAssistant']['api_key']
    async def hass_toggle_device(self, conn, entity_id, state):
        domains = entity_id.split(".")
        if len(domains) > 1:
            domain = domains[0]
        else:
            return "执行失败，错误的设备id"

        if state == "on":
            description = "打开"
            if domain == 'cover':
                action = "open_cover"
            elif domain == 'vacuum':
                action = "start"
            else:
                action = "turn_on"
        elif state == "off":
            description = "关闭"
            if domain == 'cover':
                action = "close_cover"
            elif domain == 'vacuum':
                action = "stop"
            else:
                action = "turn_off"
        else:
            return "执行失败，未知的action"
        url = f"{self.base_url}/api/services/{domain}/{action}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "entity_id": entity_id
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return f"设备已{description}"
        else:
            return f"切换失败，错误码: {response.status_code}"

    async def hass_play_music(self, conn, entity_id, media_content_id):
        url = f"{self.base_url}/api/services/music_assistant/play_media"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "entity_id": entity_id,
            "media_id": media_content_id
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return f"正在播放{media_content_id}的音乐"
        else:
            return f"音乐播放失败，错误码: {response.status_code}"
