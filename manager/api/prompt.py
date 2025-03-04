from config.logger import setup_logging
from aiohttp import web
from config.settings import update_config
from ruamel.yaml.scalarstring import PreservedScalarString
from manager.api.auth import verify_token
from manager.api.response import response_unauthorized, response_success, response_error

TAG = __name__
logger = setup_logging()

class PromptApi:
    def __init__(self, config):
        self.config = config

    async def get_prompt(self, request):
        if not await verify_token(self.config, request):
            return response_unauthorized()

        return web.json_response({
            'prompt': self.config['prompt'],
            'Access-Control-Allow-Origin': '*'
        })

    async def update_prompt(self, request):
        if not await verify_token(self.config, request):
            return response_unauthorized()

        try:
            data = await request.json()
            if 'prompt' not in data:
                return response_success()

            # 使用PreservedScalarString保留多行文本格式
            self.config['prompt'] = PreservedScalarString(data['prompt'])

            # 保存到配置文件
            update_config(self.config)

            return response_success()
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to update prompt: {e}")
            return response_error(str(e))
