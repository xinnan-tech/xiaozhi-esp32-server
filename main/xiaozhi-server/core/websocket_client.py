import websocket
import websockets
import asyncio
import threading
import time
import json
class WebSocketClient:
    def __init__(self, url, conn=None):
        """
        初始化 WebSocket 客户端
        :param url: WebSocket 服务器地址 (例如 ws://example.com/websocket)
        :param conn: 可选的连接对象
        """
        self.url = url
        self.ws = None
        self.conn = conn

    def on_message(self,ws, message):
        """当收到消息时调用"""
        if self.conn.websocket:
            try:
                if isinstance(message, str):
                    print(message)
                    self.conn.clearSpeakStatus()
                asyncio.run_coroutine_threadsafe(self.conn.websocket.send(message), self.conn.loop)
            except Exception as e:
                print(f"Failed to send message: {e}")

    def on_error(self, ws, error):
        """当发生错误时调用"""
        print(f"Error: {error}")
        import traceback
        traceback.print_exc()

    def on_close(self, ws, close_status_code, close_msg):
        """当连接关闭时调用"""
        print("### Connection closed ###")

    def on_open(self, ws):
        """当连接成功打开时调用"""
        def run():
            # 发送 JSON 消息
            self.send(json.dumps({"type":'config',"voice":self.conn.config["TTS"]["DidirectionalFlowTTS"]["voice"]}))
        threading.Thread(target=run).start()


    def send(self, message):
        """发送消息到 WebSocket 服务器"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send(message)
        else:
            print("WebSocket is not connected.")

    def connect(self):
        """连接到 WebSocket 服务器"""
        print(f"Connecting to WebSocket server at {self.url}...")
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open

        # 启动 WebSocket 客户端
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        print("WebSocket client started.")

    def close(self):
        """关闭 WebSocket 连接"""
        if self.ws:
            self.ws.close()
            print("WebSocket connection closed.")

# 示例用法
if __name__ == "__main__":
    # 创建 WebSocket 客户端实例
    client = WebSocketClient("ws://127.0.0.1:8083")

    # 连接到 WebSocket 服务器
    client.connect()
    time.sleep(1)
    client.send(json.dumps({ "type": "start" }))
    time.sleep(1)
    client.send(json.dumps({ "type": "text" , "text":'你好呀.'}))
    time.sleep(1)
    client.send(json.dumps({ "type": "finish"}))
    # 模拟运行一段时间后关闭连接
    try:
        while True:
            time.sleep(1)  # 主线程保持运行
    except KeyboardInterrupt:
        print("Closing WebSocket connection...")
        client.close()