import unittest
import json
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock heavy dependencies that might be missing in some test environments
sys.modules["numpy"] = MagicMock()
sys.modules["opuslib_next"] = MagicMock()
sys.modules["pydub"] = MagicMock()
sys.modules["loguru"] = MagicMock()
sys.modules["requests"] = MagicMock()

from core.providers.tools.device_mcp.mcp_handler import (
    MCPClient, handle_mcp_message, send_mcp_initialize_message, 
    send_mcp_tools_list_request, call_mcp_tool, sync_device_hardware_status
)

class TestMCPHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mcp_client = MCPClient()
        self.conn = MagicMock()
        self.conn.features = {"mcp": True}
        self.conn.websocket = AsyncMock()
        self.conn.mcp_client = self.mcp_client
        self.conn.mcp_battery = None
        
        # Mock func_handler for tool refresh
        self.conn.func_handler = MagicMock()
        self.conn.func_handler.tool_manager = MagicMock()
        self.conn.func_handler.tool_manager.refresh_tools = MagicMock()
        self.conn.func_handler.current_support_functions = MagicMock()

    async def test_mcp_client_tool_registration(self):
        """Test tool registration and sanitization"""
        tool_data = {
            "name": "self.dog.forward!",
            "description": "Move the dog forward",
            "inputSchema": {"type": "object", "properties": {}}
        }
        await self.mcp_client.add_tool(tool_data)
        
        # Verify sanitization (OpenAI compatibility: no '!')
        sanitized_name = "self_dog_forward_"
        self.assertTrue(self.mcp_client.has_tool(sanitized_name))
        self.assertEqual(self.mcp_client.name_mapping[sanitized_name], "self.dog.forward!")

    async def test_json_rpc_initialize_format(self):
        """Test initialize message follows JSON-RPC 2.0"""
        await send_mcp_initialize_message(self.conn)
        
        self.conn.websocket.send.assert_called_once()
        sent_msg = json.loads(self.conn.websocket.send.call_args[0][0])
        
        self.assertEqual(sent_msg["type"], "mcp")
        payload = sent_msg["payload"]
        self.assertEqual(payload["jsonrpc"], "2.0")
        self.assertEqual(payload["method"], "initialize")
        self.assertEqual(payload["id"], 1)

    async def test_handle_mcp_tools_list(self):
        """Test processing of tools/list response"""
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "get_device_status", "description": "Status info", "inputSchema": {}}
                ]
            }
        }
        
        # Use a patch to avoid background task issues in unit test
        with patch('asyncio.create_task'):
            await handle_mcp_message(self.conn, self.mcp_client, payload)
        
        self.assertTrue(self.mcp_client.ready)
        self.assertTrue(self.mcp_client.has_tool("get_device_status"))

    async def test_sync_device_battery_success(self):
        """Test battery sync sets conn.mcp_battery"""
        # Set up client to be ready
        await self.mcp_client.set_ready(True)
        await self.mcp_client.add_tool({"name": "get_device_status", "description": "", "inputSchema": {}})
        
        # Mock tool call response with nested structure
        status_response = json.dumps({
            "battery": {"level": 85, "charging": True},
            "audio_speaker": {"volume": 50},
            "wifi": "strong"
        })
        
        # Mock call_mcp_tool to return our fake status
        with patch('core.providers.tools.device_mcp.mcp_handler.call_mcp_tool', return_value=status_response):
            await sync_device_hardware_status(self.conn, "get_device_status")
            
        self.assertEqual(self.conn.mcp_battery, "85")

    async def test_sync_device_battery_alternate_key(self):
        """Test battery sync with 'level' key instead of 'battery'"""
        await self.mcp_client.set_ready(True)
        await self.mcp_client.add_tool({"name": "status", "description": "", "inputSchema": {}})
        
        status_response = json.dumps({"level": "99", "temp": 30})
        
        with patch('core.providers.tools.device_mcp.mcp_handler.call_mcp_tool', return_value=status_response):
            await sync_device_hardware_status(self.conn, "status")
            
        self.assertEqual(self.conn.mcp_battery, "99")

    async def test_tool_call_arguments_string_parsing(self):
        """Test that tools/call correctly handles string vs dict arguments"""
        await self.mcp_client.set_ready(True)
        await self.mcp_client.add_tool({"name": "set_volume", "description": "", "inputSchema": {}})
        
        # Background task to resolve the future as soon as the message is "sent"
        async def mock_resolver():
            while not self.conn.websocket.send.called:
                await asyncio.sleep(0.01)
            sent_msg = json.loads(self.conn.websocket.send.call_args[0][0])
            msg_id = sent_msg["payload"]["id"]
            await self.mcp_client.resolve_call_result(msg_id, {"content": [{"text": "ok"}]})

        asyncio.create_task(mock_resolver())
        await call_mcp_tool(self.conn, self.mcp_client, "set_volume", '{"volume": 50}', timeout=2)
        
        # Verify sent payload arguments is a DICT
        sent_msg = json.loads(self.conn.websocket.send.call_args[0][0])
        self.assertIsInstance(sent_msg["payload"]["params"]["arguments"], dict)
        self.assertEqual(sent_msg["payload"]["params"]["arguments"]["volume"], 50)

if __name__ == "__main__":
    unittest.main()
