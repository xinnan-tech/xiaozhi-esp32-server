from aiohttp import web
from config.logger import setup_logging


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

    def _add_cors_headers(self, response):
        """Add cors header information"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"
