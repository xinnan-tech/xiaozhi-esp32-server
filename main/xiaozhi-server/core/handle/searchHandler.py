import json

import requests

from config.logger import setup_logging
TAG = __name__
logger = setup_logging()

class SearchHandler:
    """传入config.searxng"""
    def __init__(self, config: dict):
        self.endpoint = config['endpoint'] or None
        self.keywords = config['keywords'] or []

    def match_keywords(self, text_input:str):
        if not self.keywords or not self.endpoint:
            return None
        logger.bind(tag=TAG).debug(f"从用户输入中提取关键词: {text_input}")
        for keyword in self.keywords:
            if keyword in text_input:
                return keyword
        return None

    def handle_music_command(self, key:str, timeout_second=5):
        response = requests.post(
            f"{self.endpoint}/search?format=json",
            data={
                'q':key,
                'categories': 'general',
                'language': 'auto',
                'time_range':'',
                'safesearch':'0',
                'theme': 'simple'
            }, timeout=timeout_second
        )
        code = response.status_code
        if code != 200:
            logger.bind(tag=TAG).info(f'search key={key} result http code = {code}')
        resp = response.content
        item_list = json.loads(resp)['results']
        logger.bind(tag=TAG).info(f'search key={key} result http code = {code} results len={len(item_list)}')
        return '\n'.join([i['content'] for i in item_list[:10]])