import uuid
from manager.api.response import response_success, response_error


async def verify_token(config, request):
    if 'token' not in config['manager']:
        return True
    expected_token = config['manager']['token']
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    if not token or token != expected_token:
        return False
    return True


class AuthApi:
    def __init__(self, config):
        self.config = config

    async def login(self, request):
        try:
            data = await request.json()
            if 'password' not in data:
                return response_error("密码不能为空")
            # 通过config参数回传修改能力
            if self.config['manager']['token'] == data['password']:
                return response_success(data=str(uuid.uuid4()))
            return response_error("密码不正确")
        except Exception as e:
            return response_error(str(e))
