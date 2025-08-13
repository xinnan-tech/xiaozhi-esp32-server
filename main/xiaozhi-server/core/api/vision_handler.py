import json
import copy
from aiohttp import web
from config.logger import setup_logging
from core.utils.util import get_vision_url, is_valid_image_file
from core.utils.vllm import create_instance
from config.config_loader import get_private_config_from_api
from core.utils.auth import AuthToken
import base64
from typing import Tuple, Optional
from plugins_func.register import Action

TAG = __name__

# Set maximum file size to 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


class VisionHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        # Initialize authentication tool
        self.auth = AuthToken(config["server"]["auth_key"])

    def _create_error_response(self, message: str) -> dict:
        """Create unified error response format"""
        return {"success": False, "message": message}

    def _verify_auth_token(self, request) -> Tuple[bool, Optional[str]]:
        """Verify authentication token"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False, None

        token = auth_header[7:]  # Remove "Bearer " prefix
        return self.auth.verify_token(token)

    async def handle_post(self, request):
        """Handle MCP Vision POST request"""
        response = None  # Initialize response variable
        try:
            # Verify token
            is_valid, token_device_id = self._verify_auth_token(request)
            if not is_valid:
                response = web.Response(
                    text=json.dumps(
                        self._create_error_response(
                            "Invalid authentication token or token expired")
                    ),
                    content_type="application/json",
                    status=401,
                )
                return response

            # Get request header information
            device_id = request.headers.get("Device-Id", "")
            client_id = request.headers.get("Client-Id", "")
            if device_id != token_device_id:
                raise ValueError("Device ID does not match token")
            # Parse multipart/form-data request
            reader = await request.multipart()

            # Read question field
            question_field = await reader.next()
            if question_field is None:
                raise ValueError("Missing question field")
            question = await question_field.text()
            self.logger.bind(tag=TAG).debug(f"Question: {question}")

            # Read image file
            image_field = await reader.next()
            if image_field is None:
                raise ValueError("Missing image file")

            # Read image data
            image_data = await image_field.read()
            if not image_data:
                raise ValueError("Image data is empty")

            # Check file size
            if len(image_data) > MAX_FILE_SIZE:
                raise ValueError(
                    f"Image size exceeds limit, maximum allowed {MAX_FILE_SIZE/1024/1024}MB"
                )

            # Check file format
            if not is_valid_image_file(image_data):
                raise ValueError(
                    "Unsupported file format, please upload a valid image file (supports JPEG, PNG, GIF, BMP, TIFF, WEBP formats)"
                )

            # Convert image to base64 encoding
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # If smart control panel is enabled, get model configuration from smart control panel
            current_config = copy.deepcopy(self.config)
            read_config_from_api = current_config.get(
                "read_config_from_api", False)
            if read_config_from_api:
                current_config = get_private_config_from_api(
                    current_config,
                    device_id,
                    client_id,
                )

            select_vllm_module = current_config["selected_module"].get("VLLM")
            if not select_vllm_module:
                raise ValueError(
                    "You have not set a default vision analysis module yet")

            vllm_type = (
                select_vllm_module
                if "type" not in current_config["VLLM"][select_vllm_module]
                else current_config["VLLM"][select_vllm_module]["type"]
            )

            if not vllm_type:
                raise ValueError(
                    f"Cannot find VLLM module corresponding provider {vllm_type}")

            vllm = create_instance(
                vllm_type, current_config["VLLM"][select_vllm_module]
            )

            result = vllm.response(question, image_base64)

            return_json = {
                "success": True,
                "action": Action.RESPONSE.name,
                "response": result,
            }

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except ValueError as e:
            self.logger.bind(tag=TAG).error(
                f"MCP Vision POST request exception: {e}")
            return_json = self._create_error_response(str(e))
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"MCP Vision POST request exception: {e}")
            return_json = self._create_error_response(
                "Error occurred while processing request")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """Handle MCP Vision GET request"""
        try:
            vision_explain = get_vision_url(self.config)
            if vision_explain and len(vision_explain) > 0 and "null" != vision_explain:
                message = (
                    f"MCP Vision interface running normally, vision explanation interface address is: {vision_explain}"
                )
            else:
                message = "MCP Vision interface not running normally, please open the .config.yaml file in the data directory, find [server.vision_explain], and set the address properly"

            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"MCP Vision GET request exception: {e}")
            return_json = self._create_error_response("Internal server error")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response

    def _add_cors_headers(self, response):
        """Add CORS header information"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"
