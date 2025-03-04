from aiohttp import web
from typing import Optional, Dict, Any  # 导入Optional用于表示可选类型


def response_error(msg):
    return web.json_response({"code": -1, 'msg': msg}, status=200)


def response_success(msg: str = '', data: Optional[Any] = None):
    if data is None:
        data = {}
    return web.json_response({"code": 0, 'msg': msg, 'data': data}, status=200)


def response_unauthorized():
    return web.json_response({"code": 401}, status=200)
