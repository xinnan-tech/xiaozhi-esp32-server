import asyncio
import json
import base64
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from config.logger import setup_logging
from typing import Dict, Any

TAG = __name__


class CameraHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        # 存储每个设备的摄像头流状态
        self.device_streams: Dict[str, Dict[str, Any]] = {}
        # 存储每个设备的帧数据队列
        self.device_frames: Dict[str, asyncio.Queue] = {}

    async def handle_start_stream(self, request: Request) -> Response:
        """启动设备摄像头推流"""
        try:
            device_id = request.match_info.get('device_id')
            if not device_id:
                return web.json_response({"error": "Device ID is required"}, status=400)
            
            # URL解码设备ID
            from urllib.parse import unquote
            device_id = unquote(device_id)
            
            # 解析请求参数
            data = await request.json() if request.content_type == 'application/json' else {}
            fps = data.get('fps', 5)
            quality = data.get('quality', 8)
            
            self.logger.bind(tag=TAG).info(f"Starting camera stream for device: {device_id}, fps: {fps}, quality: {quality}")
            
            # 存储流配置
            self.device_streams[device_id] = {
                'fps': fps,
                'quality': quality,
                'active': True
            }
            
            # 创建帧队列（如果不存在）
            if device_id not in self.device_frames:
                self.device_frames[device_id] = asyncio.Queue(maxsize=10)
            
            # 这里应该通过 WebSocket 向设备发送启动命令
            # 由于我们没有直接的设备连接引用，我们通过 Redis 发送命令
            if hasattr(self, 'redis') and self.redis:
                command = {
                    "action": "start",
                    "fps": fps,
                    "quality": quality
                }
                await self.redis.publish(f"camera:cmd:{device_id}", json.dumps(command))
                self.logger.bind(tag=TAG).info(f"Published start command to Redis for device: {device_id}")
            
            return web.json_response({"success": True, "message": "Camera stream started"})
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error starting camera stream: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_stop_stream(self, request: Request) -> Response:
        """停止设备摄像头推流"""
        try:
            device_id = request.match_info.get('device_id')
            if not device_id:
                return web.json_response({"error": "Device ID is required"}, status=400)
            
            # URL解码设备ID
            from urllib.parse import unquote
            device_id = unquote(device_id)
            
            self.logger.bind(tag=TAG).info(f"Stopping camera stream for device: {device_id}")
            
            # 更新流状态
            if device_id in self.device_streams:
                self.device_streams[device_id]['active'] = False
            
            # 清空帧队列
            if device_id in self.device_frames:
                while not self.device_frames[device_id].empty():
                    try:
                        self.device_frames[device_id].get_nowait()
                    except asyncio.QueueEmpty:
                        break
            
            # 通过 Redis 发送停止命令
            if hasattr(self, 'redis') and self.redis:
                command = {"action": "stop"}
                await self.redis.publish(f"camera:cmd:{device_id}", json.dumps(command))
                self.logger.bind(tag=TAG).info(f"Published stop command to Redis for device: {device_id}")
            
            return web.json_response({"success": True, "message": "Camera stream stopped"})
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error stopping camera stream: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_stream(self, request: Request) -> Response:
        """获取设备摄像头 MJPEG 流"""
        try:
            device_id = request.match_info.get('device_id')
            if not device_id:
                return web.json_response({"error": "Device ID is required"}, status=400)
            
            # URL解码设备ID
            from urllib.parse import unquote
            device_id = unquote(device_id)
            
            self.logger.bind(tag=TAG).info(f"Starting MJPEG stream for device: {device_id}")
            self.logger.bind(tag=TAG).info(f"Available device frames: {list(self.device_frames.keys())}")
            
            # 创建响应流
            response = web.StreamResponse()
            response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Connection'] = 'close'
            
            await response.prepare(request)
            
            # 获取设备的帧队列
            frame_queue = self.device_frames.get(device_id)
            if not frame_queue:
                # 如果队列不存在，创建一个
                frame_queue = asyncio.Queue(maxsize=10)
                self.device_frames[device_id] = frame_queue
            
            try:
                while True:
                    # 等待帧数据
                    try:
                        frame_data = await asyncio.wait_for(frame_queue.get(), timeout=5.0)
                        
                        # 发送 MJPEG 帧
                        await response.write(frame_data)
                        
                    except asyncio.TimeoutError:
                        # 超时，发送一个空帧或保持连接
                        continue
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"Error processing frame for device {device_id}: {e}")
                        break
                        
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).info(f"Stream cancelled for device: {device_id}")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Stream error for device {device_id}: {e}")
            finally:
                # 清理资源
                if device_id in self.device_frames:
                    # 清空队列
                    while not self.device_frames[device_id].empty():
                        try:
                            self.device_frames[device_id].get_nowait()
                        except asyncio.QueueEmpty:
                            break
            
            return response
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error creating stream for device {device_id}: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def add_frame(self, device_id: str, base64_data: str):
        """添加帧数据到设备的队列中"""
        try:
            self.logger.bind(tag=TAG).info(f"add_frame called for device: {device_id}")
            
            # 如果队列不存在，创建一个
            if device_id not in self.device_frames:
                self.device_frames[device_id] = asyncio.Queue(maxsize=10)
                self.logger.bind(tag=TAG).info(f"Created new frame queue for device: {device_id}")
            
            # 解码 base64 数据
            jpeg_data = base64.b64decode(base64_data)
            
            # 创建 MJPEG 帧
            header = f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg_data)}\r\n\r\n"
            frame_data = header.encode() + jpeg_data + b"\r\n"
            
            # 非阻塞方式添加到队列
            try:
                self.device_frames[device_id].put_nowait(frame_data)
                self.logger.bind(tag=TAG).info(f"Added frame to queue for device {device_id}, queue size: {self.device_frames[device_id].qsize()}")
            except asyncio.QueueFull:
                # 队列满了，移除一个旧帧，然后添加新帧
                try:
                    self.device_frames[device_id].get_nowait()
                    self.device_frames[device_id].put_nowait(frame_data)
                    self.logger.bind(tag=TAG).info(f"Queue full, replaced frame for device {device_id}")
                except asyncio.QueueEmpty:
                    pass
                        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error adding frame for device {device_id}: {e}")

    def set_redis(self, redis):
        """设置 Redis 连接"""
        self.redis = redis

    async def handle_options(self, request: Request) -> Response:
        """Handle CORS preflight requests"""
        response = web.Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
