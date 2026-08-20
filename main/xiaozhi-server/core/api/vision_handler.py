import json
import copy
import asyncio
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from aiohttp import web
from config.logger import setup_logging
from core.api.base_handler import BaseHandler
from core.utils.util import get_vision_url, is_valid_image_file
from core.utils.vllm import create_instance
from config.config_loader import get_private_config_from_api
from core.utils.auth import AuthToken
import base64
from typing import Tuple, Optional
from plugins_func.register import Action

TAG = __name__

# 设置最大文件大小为5MB
MAX_FILE_SIZE = 5 * 1024 * 1024
VISION_UPLOAD_DIR = Path(os.getenv("VISION_UPLOAD_DIR", "/uploadfile/vision"))
try:
    VISION_MAX_IMAGES_PER_DEVICE = int(
        os.getenv("VISION_MAX_IMAGES_PER_DEVICE", "200")
    )
except ValueError:
    VISION_MAX_IMAGES_PER_DEVICE = 200


class VisionHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        # 初始化认证工具
        self.auth = AuthToken(config["server"]["auth_key"])

    def _create_error_response(self, message: str) -> dict:
        """创建统一的错误响应格式"""
        return {"success": False, "message": message}

    def _get_image_extension(self, image_data: bytes) -> str:
        if image_data.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if image_data.startswith((b"GIF87a", b"GIF89a")):
            return "gif"
        if image_data.startswith(b"BM"):
            return "bmp"
        if image_data.startswith((b"II*\x00", b"MM\x00*")):
            return "tiff"
        if image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            return "webp"
        return "jpg"

    def _save_image_sync(self, device_id: str, image_data: bytes) -> str:
        device_key = re.sub(r"[^A-Za-z0-9_-]", "_", device_id) or "unknown"
        device_dir = VISION_UPLOAD_DIR / device_key
        device_dir.mkdir(parents=True, exist_ok=True)

        extension = self._get_image_extension(image_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{extension}"
        image_path = device_dir / filename
        image_path.write_bytes(image_data)

        images = sorted(
            (path for path in device_dir.iterdir() if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale_image in images[VISION_MAX_IMAGES_PER_DEVICE:]:
            stale_image.unlink(missing_ok=True)

        return f"/mcp/vision/image/{device_key}/{filename}"

    async def _save_image(self, device_id: str, image_data: bytes) -> str:
        return await asyncio.to_thread(self._save_image_sync, device_id, image_data)

    def _verify_auth_token(self, request) -> Tuple[bool, Optional[str]]:
        """验证认证token"""
        # 测试模式：允许特定测试令牌或跳过验证
        auth_header = request.headers.get("Authorization", "")
        client_id = request.headers.get("Client-Id", "")

        # 允许测试客户端跳过认证
        if client_id == "web_test_client":
            device_id = request.headers.get("Device-Id", "test_device")
            return True, device_id

        if not auth_header.startswith("Bearer "):
            return False, None

        token = auth_header[7:]  # 移除"Bearer "前缀
        return self.auth.verify_token(token)

    async def handle_post(self, request):
        """处理 MCP Vision POST 请求"""
        response = None  # 初始化response变量
        try:
            # 验证token
            is_valid, token_device_id = self._verify_auth_token(request)
            if not is_valid:
                response = web.Response(
                    text=json.dumps(
                        self._create_error_response("无效的认证token或token已过期")
                    ),
                    content_type="application/json",
                    status=401,
                )
                return response

            # 获取请求头信息
            device_id = request.headers.get("Device-Id", "")
            client_id = request.headers.get("Client-Id", "")
            if device_id != token_device_id:
                raise ValueError("设备ID与token不匹配")
            # 解析multipart/form-data请求
            reader = await request.multipart()

            # 读取question字段
            question_field = await reader.next()
            if question_field is None:
                raise ValueError("缺少问题字段")
            question = await question_field.text()
            self.logger.bind(tag=TAG).debug(f"Question: {question}")

            # 读取图片文件
            image_field = await reader.next()
            if image_field is None:
                raise ValueError("缺少图片文件")

            # 读取图片数据
            image_data = await image_field.read()
            if not image_data:
                raise ValueError("图片数据为空")

            # 检查文件大小
            if len(image_data) > MAX_FILE_SIZE:
                raise ValueError(
                    f"图片大小超过限制，最大允许{MAX_FILE_SIZE/1024/1024}MB"
                )

            # 检查文件格式
            if not is_valid_image_file(image_data):
                raise ValueError(
                    "不支持的文件格式，请上传有效的图片文件（支持JPEG、PNG、GIF、BMP、TIFF、WEBP格式）"
                )

            # 将图片转换为base64编码
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 如果开启了智控台，则从智控台获取模型配置
            current_config = copy.deepcopy(self.config)
            read_config_from_api = current_config.get("read_config_from_api", False)
            if read_config_from_api:
                current_config = await get_private_config_from_api(
                    current_config,
                    device_id,
                    client_id,
                )

            select_vllm_module = current_config["selected_module"].get("VLLM")
            if not select_vllm_module:
                raise ValueError("您还未设置默认的视觉分析模块")

            vllm_type = (
                select_vllm_module
                if "type" not in current_config["VLLM"][select_vllm_module]
                else current_config["VLLM"][select_vllm_module]["type"]
            )

            if not vllm_type:
                raise ValueError(f"无法找到VLLM模块对应的供应器{vllm_type}")

            vllm = create_instance(
                vllm_type, current_config["VLLM"][select_vllm_module]
            )

            result = vllm.response(question, image_base64)

            image_url = await self._save_image(device_id, image_data)
            self.logger.bind(tag=TAG).info(
                f"保存视觉图片: device={device_id}, size={len(image_data)}, path={image_url}"
            )

            return_json = {
                "success": True,
                "action": Action.RESPONSE.name,
                "response": result,
                "image_url": image_url,
            }

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except ValueError as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response(str(e))
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response("处理请求时发生错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    async def handle_image_get(self, request):
        """读取已保存的视觉图片。"""
        device_key = request.match_info.get("device_id", "")
        filename = request.match_info.get("filename", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", device_key) or not re.fullmatch(
            r"[A-Za-z0-9_-]+\.(jpg|jpeg|png|gif|bmp|tiff|webp)", filename
        ):
            raise web.HTTPNotFound()

        upload_root = VISION_UPLOAD_DIR.resolve()
        image_path = (upload_root / device_key / filename).resolve()
        if upload_root not in image_path.parents or not image_path.is_file():
            raise web.HTTPNotFound()

        response = web.FileResponse(image_path)
        response.headers["Cache-Control"] = "private, max-age=86400"
        self._add_cors_headers(response)
        return response

    async def handle_get(self, request):
        """处理 MCP Vision GET 请求"""
        try:
            vision_explain = get_vision_url(self.config)
            if vision_explain and len(vision_explain) > 0 and "null" != vision_explain:
                message = (
                    f"MCP Vision 接口运行正常，视觉解释接口地址是：{vision_explain}"
                )
            else:
                message = "MCP Vision 接口运行不正常，请打开data目录下的.config.yaml文件，找到【server.vision_explain】，设置好地址"

            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision GET请求异常: {e}")
            return_json = self._create_error_response("服务器内部错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response
