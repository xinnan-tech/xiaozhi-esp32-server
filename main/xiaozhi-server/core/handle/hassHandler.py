import requests
from config.logger import setup_logging


TAG = __name__
logger = setup_logging()


class HassHandler:
    def __init__(self, config):
        self.config = config
        self.base_url = config["LLM"]['HomeAssistant']['base_url']
        self.api_key = config["LLM"]['HomeAssistant']['api_key'] 
    

    async def hass_get_state(self, conn, entity_id):
        url = f"{self.base_url}/api/states/{entity_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        #logger.bind(tag=TAG).info(f"获取状态: url:{url},return_code:{response.status_code},{response.json()}")
        if response.status_code == 200:
            return response.json()['state']
            #return response.json()['attributes']
            #response.attributes
        else:
            return f"切换失败，错误码: {response.status_code}"

        
    async def hass_set_state(self, conn, entity_id, state):
        '''
        state = { "type":"brightness_up","input":"80","is_muted":"true"}
        '''
        domains = entity_id.split(".")
        if len(domains) > 1:
            domain = domains[0]
        else:
            return "执行失败，错误的设备id"
        action = ''
        arg = ''
        value = ''
        if state['type'] == 'turn_on':
            description = "设备已打开"
            if domain == "cover":
                action = "open_cover"
            elif domain == "vacuum":
                action = "start"
            else:
                action = "turn_on"
            action = 'turn_on'
        elif state['type'] == 'turn_off':
            description = "设备已关闭"
            if domain == 'cover':
                action = "close_cover"
            elif domain == 'vacuum':
                action = "stop"
            else:
                action = "turn_off"
        elif state['type'] == 'brightness_up':
            description = "灯光已调亮"
            action = 'turn_on'
            arg = 'brightness_step_pct'
            value = 10
        elif state['type'] == 'brightness_down':
            description = "灯光已调暗"
            action = 'turn_on'
            arg = 'brightness_step_pct'
            value = -10
        elif state['type'] == 'brightness_value':
            description = f"亮度已调整到{state['input']}"
            action = 'turn_on'
            arg = 'brightness_pct' 
            value = state['input']
        elif state['type'] == 'volume_up':
            description = "音量已调大"
            action = state['type']
        elif state['type'] == 'volume_down':
            description = "音量已调小"
            action = state['type']
        elif state['type'] == 'volume_set':
            description = f"音量已调整到{state['input']}"
            action = state['type']
            arg = 'volume_level'
            value = state['input']
        elif state['type'] == 'volume_mute':
            description = f"设备已静音"
            action = state['type']
            arg = 'is_volume_muted'
            value = state['is_muted']
        elif state['type'] == 'pause':
            description = f"设备已暂停"
            action = state['type']
            if domain == 'media_player':
                action = 'media_pause'
            if domain == 'cover':
                action = 'stop_cover'
            if domain == 'vacuum':
                action = 'pause'
        elif state['type'] == 'continue':
            description = f"设备已继续"
            if domain == 'media_player':
                action = 'media_play'
            if domain == 'vacuum':
                action = 'start'
        else:
            return f"{domain} {state.type}功能尚未支持"

        url = f"{self.base_url}/api/services/{domain}/{action}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if arg == '': 
            data = {
                "entity_id": entity_id,
            }
        else:
            data = {
                "entity_id": entity_id,
                arg: value
            }
        response = requests.post(url, headers=headers, json=data)
        logger.bind(tag=TAG).info(f"设置状态:url:{url},return_code:{response.status_code}")
        if response.status_code == 200:
            return description
        else:
            return f"设置失败，错误码: {response.status_code}"



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
                action = "return_to_base"
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
