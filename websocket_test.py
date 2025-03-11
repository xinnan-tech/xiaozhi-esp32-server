import asyncio
import websockets
import json
import uuid
import logging
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 命令行参数
parser = argparse.ArgumentParser(description='测试WebSocket服务器连接')
parser.add_argument('--url', type=str, default='ws://frp-bar.com:28103', help='WebSocket服务器URL')
parser.add_argument('--token', type=str, default='xZ8$kL2@qT9mW5#', help='访问令牌')
parser.add_argument('--mac', type=str, default='24:0A:C4:1D:3B:F0', help='设备MAC地址')
args = parser.parse_args()

async def test_connection():
    # 生成随机UUID作为客户端ID
    client_id = str(uuid.uuid4())
    device_mac = args.mac
    token = args.token
    ws_url = args.url
    
    # 准备连接头信息
    headers = {
        'Authorization': f'Bearer {token}',
        'Protocol-Version': '1',
        'Device-Id': device_mac,
        'Client-Id': client_id
    }
    
    try:
        logger.info(f"尝试连接到 {ws_url}")
        logger.info(f"使用设备ID: {device_mac}, 客户端ID: {client_id}")
        
        # 建立WebSocket连接
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            logger.info("连接已建立，发送hello消息")
            
            # 发送hello消息
            hello_message = {
                "type": "hello",
                "version": 1,
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,
                    "channels": 1,
                    "frame_duration": 60
                }
            }
            
            await websocket.send(json.dumps(hello_message))
            logger.info(f"已发送: {json.dumps(hello_message, ensure_ascii=False)}")
            
            # 接收服务器响应
            response = await websocket.recv()
            try:
                response_json = json.loads(response)
                logger.info(f"服务器响应: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                
                # 如果收到hello响应，发送一个listen消息进行进一步测试
                if response_json.get("type") == "hello":
                    logger.info("握手成功，发送listen消息测试...")
                    
                    # 发送开始监听消息
                    listen_message = {
                        "session_id": "",  # WebSocket协议不需要session_id
                        "type": "listen",
                        "state": "start",
                        "mode": "manual"  # 使用手动模式
                    }
                    
                    await websocket.send(json.dumps(listen_message))
                    logger.info(f"已发送: {json.dumps(listen_message, ensure_ascii=False)}")
                    
                    # 等待服务器响应（可能是任何类型的消息）
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    try:
                        response_json = json.loads(response)
                        logger.info(f"服务器响应: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        # 可能是二进制数据
                        logger.info(f"接收到非JSON响应，可能是二进制数据，长度: {len(response)} 字节")
                    
                    # 发送停止监听消息
                    stop_message = {
                        "session_id": "",
                        "type": "listen",
                        "state": "stop"
                    }
                    
                    await websocket.send(json.dumps(stop_message))
                    logger.info(f"已发送: {json.dumps(stop_message, ensure_ascii=False)}")
                    
                    # 再等待一个响应
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        try:
                            response_json = json.loads(response)
                            logger.info(f"服务器响应: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                        except json.JSONDecodeError:
                            logger.info(f"接收到非JSON响应，可能是二进制数据，长度: {len(response)} 字节")
                    except asyncio.TimeoutError:
                        logger.info("等待响应超时，这可能是正常的")
            
            except json.JSONDecodeError:
                # 如果响应不是JSON格式
                logger.warning(f"接收到非JSON响应: {response[:100]}...")
            
            logger.info("测试完成，连接正常工作")
            
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    if result:
        logger.info("✅ 公网连接测试成功！WebSocket服务器可以通过公网访问。")
    else:
        logger.error("❌ 公网连接测试失败！请检查内网穿透和服务器配置。") 