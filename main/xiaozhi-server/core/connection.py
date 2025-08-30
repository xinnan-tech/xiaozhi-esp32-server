# import os
# import sys
# import copy
# import json
# import uuid
# import time
# import queue
# import asyncio
# import threading
# import traceback
# import subprocess
# import websockets
# from core.utils.util import (
#     extract_json_from_string,
#     check_vad_update,
#     check_asr_update,
#     filter_sensitive_info,
# )
# from typing import Dict, Any
# from collections import deque
# from core.utils.modules_initialize import (
#     initialize_modules,
#     initialize_tts,
#     initialize_asr,
# )
# from core.handle.reportHandle import report
# from core.providers.tts.default import DefaultTTS
# from concurrent.futures import ThreadPoolExecutor
# from core.utils.dialogue import Message, Dialogue
# from core.providers.asr.dto.dto import InterfaceType
# from core.handle.textHandle import handleTextMessage
# from core.providers.tools.unified_tool_handler import UnifiedToolHandler
# from plugins_func.loadplugins import auto_import_modules
# from plugins_func.register import Action, ActionResponse
# from core.auth import AuthMiddleware, AuthenticationError
# from config.config_loader import get_private_config_from_api
# from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
# from config.logger import setup_logging, build_module_string, create_connection_logger
# from config.manage_api_client import DeviceNotFoundException, DeviceBindException
# from core.utils.prompt_manager import PromptManager
# from core.utils.voiceprint_provider import VoiceprintProvider
# from core.utils import textUtils

# TAG = __name__

# auto_import_modules("plugins_func.functions")


# class TTSException(RuntimeError):
#     pass


# class ConnectionHandler:
#     def __init__(
#         self,
#         config: Dict[str, Any],
#         _vad,
#         _asr,
#         _llm,
#         _memory,
#         _intent,
#         server=None,
#     ):
#         self.common_config = config
#         self.config = copy.deepcopy(config)
#         self.session_id = str(uuid.uuid4())
#         self.logger = setup_logging()
#         self.server = server  # Save a reference to the server instance

#         self.auth = AuthMiddleware(config)
#         self.need_bind = False
#         self.bind_code = None
#         self.read_config_from_api = self.config.get(
#             "read_config_from_api", False)

#         self.websocket = None
#         self.headers = None
#         self.device_id = None
#         self.client_ip = None
#         self.prompt = None
#         self.welcome_msg = None
#         self.max_output_size = 0
#         self.chat_history_conf = 0
#         self.audio_format = "opus"

#         # Client state related
#         self.client_abort = False
#         self.client_is_speaking = False
#         self.client_listen_mode = "auto"

#         # Thread task related
#         self.loop = asyncio.get_event_loop()
#         self.stop_event = threading.Event()
#         self.executor = ThreadPoolExecutor(max_workers=5)

#         # Add reporting thread pool
#         self.report_queue = queue.Queue()
#         self.report_thread = None
#         # This can be modified in the future to adjust ASR and TTS reporting. Currently, both are enabled by default.
#         self.report_asr_enable = self.read_config_from_api
#         self.report_tts_enable = self.read_config_from_api

#         # Dependent components
#         self.vad = None
#         self.asr = None
#         self.tts = None
#         self._asr = _asr
#         self._vad = _vad
#         self.llm = _llm
#         self.memory = _memory
#         self.intent = _intent

#         # Manage voiceprint recognition separately for each connection
#         self.voiceprint_provider = None

#         # VAD related variables
#         self.client_audio_buffer = bytearray()
#         self.client_have_voice = False
#         # Unified activity timestamp (milliseconds)
#         self.last_activity_time = 0.0
#         self.client_voice_stop = False
#         self.client_voice_window = deque(maxlen=5)
#         self.last_is_voice = False

#         # ASR related variables
#         # Since a public local ASR might be used in actual deployment, variables cannot be exposed to the public ASR.
#         # Therefore, variables related to ASR need to be defined here as private variables of the connection.
#         self.asr_audio = []
#         self.asr_audio_queue = queue.Queue()
        
#         # Pre-buffer to store audio chunks before voice detection
#         # This helps capture the beginning of speech that might be missed
#         self.audio_pre_buffer = deque(maxlen=10)  # Store last 10 chunks (600ms) before voice detection
        
#         # Audio recording timeout tracking
#         self.audio_recording_start_time = None  # When voice recording started
#         self.max_audio_recording_seconds = 10  # Maximum recording duration in seconds

#         # LLM related variables
#         self.llm_finish_task = True
#         self.dialogue = Dialogue()

#         # TTS related variables
#         self.sentence_id = None
#         # Handle cases where TTS response has no text
#         self.tts_MessageText = ""

#         # IoT related variables
#         self.iot_descriptors = {}
#         self.func_handler = None

#         self.cmd_exit = self.config["exit_commands"]
#         self.max_cmd_length = 0
#         for cmd in self.cmd_exit:
#             if len(cmd) > self.max_cmd_length:
#                 self.max_cmd_length = len(cmd)

#         # Whether to close the connection after the chat ends
#         self.close_after_chat = False
#         self.load_function_plugin = False
#         self.intent_type = "nointent"

#         self.timeout_seconds = (
#             int(self.config.get("close_connection_no_voice_time", 120)) + 60
#         )  # Add 60 seconds to the original first-level close for a second-level close
#         self.timeout_task = None

#         # {"mcp":true} indicates that the MCP function is enabled
#         self.features = None

#         # Initialize prompt manager
#         self.prompt_manager = PromptManager(config, self.logger)

#     async def handle_connection(self, ws):
#         try:
#             # Get and validate headers
#             self.headers = dict(ws.request.headers)

#             if self.headers.get("device-id", None) is None:
#                 # Try to get device-id from the URL's query parameters
#                 from urllib.parse import parse_qs, urlparse

#                 # Get the path from the WebSocket request
#                 request_path = ws.request.path
#                 if not request_path:
#                     self.logger.bind(tag=TAG).error(
#                         "Unable to get request path")
#                     return
#                 parsed_url = urlparse(request_path)
#                 query_params = parse_qs(parsed_url.query)
#                 if "device-id" in query_params:
#                     self.headers["device-id"] = query_params["device-id"][0]
#                     self.headers["client-id"] = query_params["client-id"][0]
#                 else:
#                     await ws.send("Port is normal. To test the connection, please use test_page.html")
#                     await self.close(ws)
#                     return
#             real_ip = self.headers.get("x-real-ip") or self.headers.get(
#                 "x-forwarded-for"
#             )
#             if real_ip:
#                 self.client_ip = real_ip.split(",")[0].strip()
#             else:
#                 self.client_ip = ws.remote_address[0]
#             self.logger.bind(tag=TAG).info(
#                 f"{self.client_ip} conn - Headers: {self.headers}"
#             )

#             # Perform authentication
#             await self.auth.authenticate(self.headers)

#             # Authentication passed, continue processing
#             self.websocket = ws
#             self.device_id = self.headers.get("device-id", None)

#             # Initialize activity timestamp
#             self.last_activity_time = time.time() * 1000

#             # Start timeout check task
#             self.timeout_task = asyncio.create_task(self._check_timeout())

#             self.welcome_msg = self.config["xiaozhi"]
#             self.welcome_msg["session_id"] = self.session_id

#             # Get differential configuration
#             self._initialize_private_config()
#             # Asynchronous initialization
#             self.executor.submit(self._initialize_components)

#             try:
#                 async for message in self.websocket:
#                     await self._route_message(message)
#             except websockets.exceptions.ConnectionClosed:
#                 self.logger.bind(tag=TAG).info("Client disconnected")

#         except AuthenticationError as e:
#             self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
#             return
#         except Exception as e:
#             stack_trace = traceback.format_exc()
#             self.logger.bind(tag=TAG).error(
#                 f"Connection error: {str(e)}-{stack_trace}")
#             return
#         finally:
#             try:
#                 await self._save_and_close(ws)
#             except Exception as final_error:
#                 self.logger.bind(tag=TAG).error(
#                     f"Error during final cleanup: {final_error}")
#                 # Ensure the connection is closed even if saving memory fails
#                 try:
#                     await self.close(ws)
#                 except Exception as close_error:
#                     self.logger.bind(tag=TAG).error(
#                         f"Error during forced connection closure: {close_error}"
#                     )

#     async def _save_and_close(self, ws):
#         """Save memory and close the connection"""
#         try:
#             if self.memory:
#                 # Log where memory is being saved based on memory type
#                 memory_type = getattr(self, 'memory_type', 'unknown')
#                 if memory_type == "nomem":
#                     self.logger.bind(tag=TAG).info("Memory saving DISABLED (using nomem)")
#                 elif memory_type == "mem0ai":
#                     self.logger.bind(tag=TAG).info("Saving memory to MEM0 CLOUD")
#                 elif memory_type == "mem_local_short":
#                     self.logger.bind(tag=TAG).info("Saving memory to LOCAL STORAGE (mem_local_short)")
#                 else:
#                     self.logger.bind(tag=TAG).info(f"Saving memory using: {memory_type}")
                
#                 # Use a thread pool to save memory asynchronously
#                 def save_memory_task():
#                     try:
#                         self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Starting memory save task for {memory_type}")
#                         self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Dialogue messages count: {len(self.dialogue.dialogue) if self.dialogue and self.dialogue.dialogue else 0}")
                        
#                         # Create a new event loop (to avoid conflicts with the main loop)
#                         loop = asyncio.new_event_loop()
#                         asyncio.set_event_loop(loop)
                        
#                         self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Calling memory.save_memory()")
#                         result = loop.run_until_complete(
#                             self.memory.save_memory(self.dialogue.dialogue)
#                         )
                        
#                         if result:
#                             self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Memory saved successfully using {memory_type}. Result: {result}")
#                         else:
#                             self.logger.bind(tag=TAG).warning(f"[MEM0-THREAD] Memory save returned None/False for {memory_type}")
#                     except Exception as e:
#                         self.logger.bind(tag=TAG).error(
#                             f"[MEM0-THREAD] Failed to save memory: {e}")
#                         self.logger.bind(tag=TAG).error(
#                             f"[MEM0-THREAD] Exception traceback: {traceback.format_exc()}")
#                     finally:
#                         try:
#                             loop.close()
#                         except Exception:
#                             pass

#                 # Start a thread to save memory, do not wait for completion
#                 self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Starting new thread for memory save")
#                 threading.Thread(target=save_memory_task, daemon=True).start()
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(f"Failed to save memory: {e}")
#         finally:
#             # Close the connection immediately, do not wait for memory saving to complete
#             try:
#                 await self.close(ws)
#             except Exception as close_error:
#                 self.logger.bind(tag=TAG).error(
#                     f"Failed to close connection after saving memory: {close_error}"
#                 )

#     async def _route_message(self, message):
#         """Message routing"""
#         if isinstance(message, str):
#             await handleTextMessage(self, message)
#         elif isinstance(message, bytes):
#             if self.vad is None:
#                 return
#             if self.asr is None:
#                 return
#             self.asr_audio_queue.put(message)

#     async def handle_restart(self, message):
#         """Handle server restart request"""
#         try:

#             self.logger.bind(tag=TAG).info(
#                 "Received server restart command, preparing to execute...")

#             # Send confirmation response
#             await self.websocket.send(
#                 json.dumps(
#                     {
#                         "type": "server",
#                         "status": "success",
#                         "message": "Server restarting...",
#                         "content": {"action": "restart"},
#                     }
#                 )
#             )

#             # Asynchronously execute the restart operation
#             def restart_server():
#                 """The actual method to execute the restart"""
#                 time.sleep(1)
#                 self.logger.bind(tag=TAG).info("Executing server restart...")
#                 subprocess.Popen(
#                     [sys.executable, "app.py"],
#                     stdin=sys.stdin,
#                     stdout=sys.stdout,
#                     stderr=sys.stderr,
#                     start_new_session=True,
#                 )
#                 os._exit(0)

#             # Use a thread to execute the restart to avoid blocking the event loop
#             threading.Thread(target=restart_server, daemon=True).start()

#         except Exception as e:
#             self.logger.bind(tag=TAG).error(f"Restart failed: {str(e)}")
#             await self.websocket.send(
#                 json.dumps(
#                     {
#                         "type": "server",
#                         "status": "error",
#                         "message": f"Restart failed: {str(e)}",
#                         "content": {"action": "restart"},
#                     }
#                 )
#             )

#     def _initialize_components(self):
#         try:
#             self.selected_module_str = build_module_string(
#                 self.config.get("selected_module", {})
#             )
#             self.logger = create_connection_logger(self.selected_module_str)

#             """Initialize components"""
#             if self.config.get("prompt") is not None:
#                 user_prompt = self.config["prompt"]
#                 # Use a quick prompt for initialization
#                 prompt = self.prompt_manager.get_quick_prompt(user_prompt)
#                 self.change_system_prompt(prompt)
#                 self.logger.bind(tag=TAG).info(
#                     f"Quickly initialized component: prompt successful {prompt[:50]}..."
#                 )

#             """Initialize local components"""
#             if self.vad is None:
#                 self.vad = self._vad
#             if self.asr is None:
#                 self.asr = self._initialize_asr()

#             # Initialize voiceprint recognition
#             self._initialize_voiceprint()

#             # Open speech recognition channel
#             asyncio.run_coroutine_threadsafe(
#                 self.asr.open_audio_channels(self), self.loop
#             )
#             if self.tts is None:
#                 self.tts = self._initialize_tts()
#             # Open speech synthesis channel
#             asyncio.run_coroutine_threadsafe(
#                 self.tts.open_audio_channels(self), self.loop
#             )

#             """Load memory"""
#             self._initialize_memory()
#             """Load intent recognition"""
#             self._initialize_intent()
#             """Initialize reporting thread"""
#             self._init_report_threads()
#             """Update system prompt"""
#             self._init_prompt_enhancement()

#         except Exception as e:
#             self.logger.bind(tag=TAG).error(
#                 f"Failed to instantiate components: {e}")

#     def _init_prompt_enhancement(self):
#         # Update context information
#         self.prompt_manager.update_context_info(self, self.client_ip)
#         enhanced_prompt = self.prompt_manager.build_enhanced_prompt(
#             self.config["prompt"], self.device_id, self.client_ip
#         )
#         if enhanced_prompt:
#             self.change_system_prompt(enhanced_prompt)
#             self.logger.bind(tag=TAG).info(
#                 "System prompt has been enhanced and updated")

#     def _init_report_threads(self):
#         """Initialize ASR and TTS reporting threads"""
#         if not self.read_config_from_api or self.need_bind:
#             return
#         if self.chat_history_conf == 0:
#             return
#         if self.report_thread is None or not self.report_thread.is_alive():
#             self.report_thread = threading.Thread(
#                 target=self._report_worker, daemon=True
#             )
#             self.report_thread.start()
#             self.logger.bind(tag=TAG).info("TTS reporting thread started")

#     def _initialize_tts(self):
#         """Initialize TTS"""
#         tts = None
#         if not self.need_bind:
#             tts = initialize_tts(self.config)

#         if tts is None:
#             tts = DefaultTTS(self.config, delete_audio_file=True)

#         return tts

#     def _initialize_asr(self):
#         """Initialize ASR"""
#         if self._asr.interface_type == InterfaceType.LOCAL:
#             # If the public ASR is a local service, return directly
#             # Because one local ASR instance can be shared by multiple connections
#             asr = self._asr
#         else:
#             # If the public ASR is a remote service, initialize a new instance
#             # Because a remote ASR involves a WebSocket connection and a receiving thread, each connection needs its own instance
#             asr = initialize_asr(self.config)

#         return asr

#     def _initialize_voiceprint(self):
#         """Initialize voiceprint recognition for the current connection"""
#         try:
#             voiceprint_config = self.config.get("voiceprint", {})
#             if voiceprint_config:
#                 self.voiceprint_provider = VoiceprintProvider(
#                     voiceprint_config)
#                 self.logger.bind(tag=TAG).info(
#                     "Voiceprint recognition function dynamically enabled on connection")
#             else:
#                 self.logger.bind(tag=TAG).info(
#                     "Voiceprint recognition function not enabled or configuration is incomplete")
#         except Exception as e:
#             self.logger.bind(tag=TAG).warning(
#                 f"Voiceprint recognition initialization failed: {str(e)}")

#     def _initialize_private_config(self):
#         """If getting from the configuration file, perform a second instantiation"""
#         if not self.read_config_from_api:
#             return
#         """Get differential configuration from the interface for a second instantiation, not a full re-instantiation"""
#         try:
#             begin_time = time.time()
#             private_config = get_private_config_from_api(
#                 self.config,
#                 self.headers.get("device-id"),
#                 self.headers.get("client-id", self.headers.get("device-id")),
#             )
#             private_config["delete_audio"] = bool(
#                 self.config.get("delete_audio", True))
#             # Log the actual API key status for debugging (without exposing the full key)
#             if "Memory" in private_config and "Memory_mem0ai" in private_config.get("Memory", {}):
#                 mem0_config = private_config["Memory"]["Memory_mem0ai"]
#                 api_key = mem0_config.get("api_key", "")
                
#                 # DEBUG: Print the full API key to verify what's being received
#                 self.logger.bind(tag=TAG).info(f"[DEBUG] Raw mem0 API key received: '{api_key}'")
                
#                 if api_key == "***":
#                     self.logger.bind(tag=TAG).warning(
#                         "Mem0 API key is MASKED (***) from manager API - please configure the actual API key in the Manager Web Dashboard under Provider Management"
#                     )
#                 elif api_key:
#                     masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
#                     self.logger.bind(tag=TAG).debug(f"Mem0 API key received: {masked_key} (length: {len(api_key)})")
#                 else:
#                     self.logger.bind(tag=TAG).warning("Mem0 API key is empty in differential configuration")
            
#             self.logger.bind(tag=TAG).info(
#                 f"{time.time() - begin_time} seconds, successfully obtained differential configuration: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
#             )
#         except DeviceNotFoundException as e:
#             self.need_bind = True
#             private_config = {}
#         except DeviceBindException as e:
#             self.need_bind = True
#             self.bind_code = e.bind_code
#             private_config = {}
#         except Exception as e:
#             self.need_bind = True
#             self.logger.bind(tag=TAG).error(
#                 f"Failed to get differential configuration: {e}")
#             private_config = {}

#         init_llm, init_tts, init_memory, init_intent = (
#             False,
#             False,
#             False,
#             False,
#         )

#         init_vad = check_vad_update(self.common_config, private_config)
#         init_asr = check_asr_update(self.common_config, private_config)

#         if init_vad:
#             self.config["VAD"] = private_config["VAD"]
#             self.config["selected_module"]["VAD"] = private_config["selected_module"][
#                 "VAD"
#             ]
#         if init_asr:
#             self.config["ASR"] = private_config["ASR"]
#             self.config["selected_module"]["ASR"] = private_config["selected_module"][
#                 "ASR"
#             ]
#         if private_config.get("TTS", None) is not None:
#             init_tts = True
#             self.config["TTS"] = private_config["TTS"]
#             self.config["selected_module"]["TTS"] = private_config["selected_module"][
#                 "TTS"
#             ]
#         if private_config.get("LLM", None) is not None:
#             init_llm = True
#             self.config["LLM"] = private_config["LLM"]
#             self.config["selected_module"]["LLM"] = private_config["selected_module"][
#                 "LLM"
#             ]
#         if private_config.get("VLLM", None) is not None:
#             self.config["VLLM"] = private_config["VLLM"]
#             self.config["selected_module"]["VLLM"] = private_config["selected_module"][
#                 "VLLM"
#             ]
#         if private_config.get("Memory", None) is not None:
#             init_memory = True
#             self.config["Memory"] = private_config["Memory"]
#             self.config["selected_module"]["Memory"] = private_config[
#                 "selected_module"
#             ]["Memory"]
#         if private_config.get("Intent", None) is not None:
#             init_intent = True
#             self.config["Intent"] = private_config["Intent"]
#             model_intent = private_config.get(
#                 "selected_module", {}).get("Intent", {})
#             self.config["selected_module"]["Intent"] = model_intent
#             # Load plugin configuration
#             if model_intent != "Intent_nointent":
#                 plugin_from_server = private_config.get("plugins", {})
#                 for plugin, config_str in plugin_from_server.items():
#                     plugin_from_server[plugin] = json.loads(config_str)
#                 self.config["plugins"] = plugin_from_server
#                 self.config["Intent"][self.config["selected_module"]["Intent"]][
#                     "functions"
#                 ] = list(plugin_from_server.keys())
#         if private_config.get("prompt", None) is not None:
#             self.config["prompt"] = private_config["prompt"]
#         # Get voiceprint information
#         if private_config.get("voiceprint", None) is not None:
#             self.config["voiceprint"] = private_config["voiceprint"]
#         if private_config.get("summaryMemory", None) is not None:
#             self.config["summaryMemory"] = private_config["summaryMemory"]
#         if private_config.get("device_max_output_size", None) is not None:
#             self.max_output_size = int(
#                 private_config["device_max_output_size"])
#         if private_config.get("chat_history_conf", None) is not None:
#             self.chat_history_conf = int(private_config["chat_history_conf"])
#         if private_config.get("mcp_endpoint", None) is not None:
#             self.config["mcp_endpoint"] = private_config["mcp_endpoint"]
#         try:
#             modules = initialize_modules(
#                 self.logger,
#                 private_config,
#                 init_vad,
#                 init_asr,
#                 init_llm,
#                 init_tts,
#                 init_memory,
#                 init_intent,
#             )
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(
#                 f"Failed to initialize components: {e}")
#             modules = {}
#         if modules.get("tts", None) is not None:
#             self.tts = modules["tts"]
#         if modules.get("vad", None) is not None:
#             self.vad = modules["vad"]
#         if modules.get("asr", None) is not None:
#             self.asr = modules["asr"]
#         if modules.get("llm", None) is not None:
#             self.llm = modules["llm"]
#         if modules.get("intent", None) is not None:
#             self.intent = modules["intent"]
#         if modules.get("memory", None) is not None:
#             self.memory = modules["memory"]

#     def _initialize_memory(self):
#         if self.memory is None:
#             return
#         """Initialize memory module"""
#         self.memory.init_memory(
#             role_id=self.device_id,
#             llm=self.llm,
#             summary_memory=self.config.get("summaryMemory", None),
#             save_to_file=not self.read_config_from_api,
#         )

#         # Get memory summary configuration
#         memory_config = self.config["Memory"]
#         memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
#             "type"
#         ]
#         # Store memory type for logging
#         self.memory_type = memory_type
        
#         # If using nomem, return directly
#         if memory_type == "nomem":
#             self.logger.bind(tag=TAG).info("Memory module initialized: DISABLED (nomem)")
#             return
#         # Use mem_local_short mode
#         elif memory_type == "mem_local_short":
#             self.logger.bind(tag=TAG).info("Memory module initialized: LOCAL STORAGE (mem_local_short)")
#             memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
#                 "llm"
#             ]
#             if memory_llm_name and memory_llm_name in self.config["LLM"]:
#                 # If a dedicated LLM is configured, create an independent LLM instance
#                 from core.utils import llm as llm_utils

#                 memory_llm_config = self.config["LLM"][memory_llm_name]
#                 memory_llm_type = memory_llm_config.get(
#                     "type", memory_llm_name)
#                 memory_llm = llm_utils.create_instance(
#                     memory_llm_type, memory_llm_config
#                 )
#                 self.logger.bind(tag=TAG).info(
#                     f"Created a dedicated LLM for memory summary: {memory_llm_name}, type: {memory_llm_type}"
#                 )
#                 self.memory.set_llm(memory_llm)
#             else:
#                 # Otherwise use main LLM
#                 self.memory.set_llm(self.llm)
#                 self.logger.bind(tag=TAG).info(
#                     "Using main LLM as memory model")
#         elif memory_type == "mem0ai":
#             self.logger.bind(tag=TAG).info("Memory module initialized: MEM0 CLOUD (mem0ai)")
#         else:
#             self.logger.bind(tag=TAG).info(f"Memory module initialized: {memory_type}")

#     def _initialize_intent(self):
#         if self.intent is None:
#             return
#         self.intent_type = self.config["Intent"][
#             self.config["selected_module"]["Intent"]
#         ]["type"]
#         if self.intent_type == "function_call" or self.intent_type == "intent_llm":
#             self.load_function_plugin = True
#         """Initialize intent recognition module"""
#         # Get intent recognition configuration
#         intent_config = self.config["Intent"]
#         intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
#             "type"
#         ]

#         # If using nointent, return directly
#         if intent_type == "nointent":
#             return
#         # Use intent_llm mode
#         elif intent_type == "intent_llm":
#             intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
#                 "llm"
#             ]

#             if intent_llm_name and intent_llm_name in self.config["LLM"]:
#                 # If a dedicated LLM is configured, create an independent LLM instance
#                 from core.utils import llm as llm_utils

#                 intent_llm_config = self.config["LLM"][intent_llm_name]
#                 intent_llm_type = intent_llm_config.get(
#                     "type", intent_llm_name)
#                 intent_llm = llm_utils.create_instance(
#                     intent_llm_type, intent_llm_config
#                 )
#                 self.logger.bind(tag=TAG).info(
#                     f"Created a dedicated LLM for intent recognition: {intent_llm_name}, type: {intent_llm_type}"
#                 )
#                 self.intent.set_llm(intent_llm)
#             else:
#                 # Otherwise use main LLM
#                 self.intent.set_llm(self.llm)
#                 self.logger.bind(tag=TAG).info(
#                     "Using main LLM as intent recognition model")

#         """Load unified tool handler"""
#         self.func_handler = UnifiedToolHandler(self)

#         # Asynchronously initialize tool handler
#         if hasattr(self, "loop") and self.loop:
#             asyncio.run_coroutine_threadsafe(
#                 self.func_handler._initialize(), self.loop)

#     def change_system_prompt(self, prompt):
#         self.prompt = prompt
#         # Update system prompt in the context
#         self.dialogue.update_system_message(self.prompt)

#     def chat(self, query, tool_call=False, depth=0):
#         self.logger.bind(tag=TAG).info(f"LLM received user message: {query}")
#         self.llm_finish_task = False

#         if not tool_call:
#             self.dialogue.put(Message(role="user", content=query))

#         # Create a new session ID and send a FIRST request for the top-level call
#         if depth == 0:
#             self.sentence_id = str(uuid.uuid4().hex)
#             self.tts.tts_text_queue.put(
#                 TTSMessageDTO(
#                     sentence_id=self.sentence_id,
#                     sentence_type=SentenceType.FIRST,
#                     content_type=ContentType.ACTION,
#                 )
#             )

#         # Define intent functions
#         functions = None
#         if self.intent_type == "function_call" and hasattr(self, "func_handler"):
#             functions = self.func_handler.get_functions()
#         response_message = []

#         try:
#             # Use dialogue with memory
#             memory_str = None
#             if self.memory is not None:
#                 future = asyncio.run_coroutine_threadsafe(
#                     self.memory.query_memory(query), self.loop
#                 )
#                 memory_str = future.result()

#             if self.intent_type == "function_call" and functions is not None:
#                 # Use streaming interface that supports functions
#                 llm_responses = self.llm.response_with_functions(
#                     self.session_id,
#                     self.dialogue.get_llm_dialogue_with_memory(
#                         memory_str, self.config.get("voiceprint", {})
#                     ),
#                     functions=functions,
#                 )
#             else:
#                 llm_responses = self.llm.response(
#                     self.session_id,
#                     self.dialogue.get_llm_dialogue_with_memory(
#                         memory_str, self.config.get("voiceprint", {})
#                     ),
#                 )
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(
#                 f"LLM processing error for '{query}': {e}")
            
#             ##Hre to 
            
#             # Send error message to client and ensure proper completion
#             if depth == 0:
#                 error_message = "Sorry, I'm having trouble understanding right now. Please try again."
#                 self.tts.tts_text_queue.put(
#                     TTSMessageDTO(
#                         sentence_id=self.sentence_id,
#                         sentence_type=SentenceType.MIDDLE,
#                         content_type=ContentType.TEXT,
#                         content_detail=error_message,
#                     )
#                 )
#                 # Send completion signal
#                 self.tts.tts_text_queue.put(
#                     TTSMessageDTO(
#                         sentence_id=self.sentence_id,
#                         sentence_type=SentenceType.LAST,
#                         content_type=ContentType.ACTION,
#                     )
#                 )
            
#             self.llm_finish_task = True

#             #here
#             return None

#         # Handle streaming response
#         tool_call_flag = False
#         function_name = None
#         function_id = None
#         function_arguments = ""
#         content_arguments = ""
#         self.client_abort = False
#         emotion_flag = True
#         for response in llm_responses:
#             if self.client_abort:
#                 break
#             if self.intent_type == "function_call" and functions is not None:
#                 content, tools_call = response
#                 if "content" in response:
#                     content = response["content"]
#                     tools_call = None
#                 if content is not None and len(content) > 0:
#                     content_arguments += content

#                 if not tool_call_flag and content_arguments.startswith("<tool_call>"):
#                     # print("content_arguments", content_arguments)
#                     tool_call_flag = True

#                 if tools_call is not None and len(tools_call) > 0:
#                     tool_call_flag = True
#                     if tools_call[0].id is not None:
#                         function_id = tools_call[0].id
#                     if tools_call[0].function.name is not None:
#                         function_name = tools_call[0].function.name
#                     if tools_call[0].function.arguments is not None:
#                         function_arguments += tools_call[0].function.arguments
#             else:
#                 content = response

#             # Get emotion from LLM reply, only once at the beginning of a conversation turn
#             if emotion_flag and content is not None and content.strip():
#                 asyncio.run_coroutine_threadsafe(
#                     textUtils.get_emotion(self, content),
#                     self.loop,
#                 )
#                 emotion_flag = False

#             if content is not None and len(content) > 0:
#                 if not tool_call_flag:
#                     response_message.append(content)
#                     self.tts.tts_text_queue.put(
#                         TTSMessageDTO(
#                             sentence_id=self.sentence_id,
#                             sentence_type=SentenceType.MIDDLE,
#                             content_type=ContentType.TEXT,
#                             content_detail=content,
#                         )
#                     )
#         # Handle function call
#         if tool_call_flag:
#             bHasError = False
#             if function_id is None:
#                 a = extract_json_from_string(content_arguments)
#                 if a is not None:
#                     try:
#                         content_arguments_json = json.loads(a)
#                         function_name = content_arguments_json["name"]
#                         function_arguments = json.dumps(
#                             content_arguments_json["arguments"], ensure_ascii=False
#                         )
#                         function_id = str(uuid.uuid4().hex)
#                     except Exception as e:
#                         bHasError = True
#                         response_message.append(a)
#                 else:
#                     bHasError = True
#                     response_message.append(content_arguments)
#                 if bHasError:
#                     self.logger.bind(tag=TAG).error(
#                         f"function call error: {content_arguments}"
#                     )
#             if not bHasError:
#                 # If the LLM needs to process a turn first, add relevant processed log information
#                 if len(response_message) > 0:
#                     text_buff = "".join(response_message)
#                     self.tts_MessageText = text_buff
#                     self.dialogue.put(
#                         Message(role="assistant", content=text_buff))
#                 response_message.clear()
#                 self.logger.bind(tag=TAG).debug(
#                     f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
#                 )
#                 function_call_data = {
#                     "name": function_name,
#                     "id": function_id,
#                     "arguments": function_arguments,
#                 }

#                 # Use unified tool handler to process all tool calls
#                 result = asyncio.run_coroutine_threadsafe(
#                     self.func_handler.handle_llm_function_call(
#                         self, function_call_data
#                     ),
#                     self.loop,
#                 ).result()
#                 self._handle_function_result(
#                     result, function_call_data, depth=depth)

#         # Store dialogue content
#         if len(response_message) > 0:
#             text_buff = "".join(response_message)
#             self.tts_MessageText = text_buff
#             self.dialogue.put(Message(role="assistant", content=text_buff))
#         if depth == 0:
#             self.tts.tts_text_queue.put(
#                 TTSMessageDTO(
#                     sentence_id=self.sentence_id,
#                     sentence_type=SentenceType.LAST,
#                     content_type=ContentType.ACTION,
#                 )
#             )
#         self.llm_finish_task = True
#         # Use lambda for delayed calculation, get_llm_dialogue() is only executed at DEBUG level
#         self.logger.bind(tag=TAG).debug(
#             lambda: json.dumps(
#                 self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False
#             )
#         )

#         return True

#     def _handle_function_result(self, result, function_call_data, depth):
#         if result.action == Action.RESPONSE:  # Respond directly to the front-end
#             text = result.response
#             self.tts.tts_one_sentence(
#                 self, ContentType.TEXT, content_detail=text)
#             self.dialogue.put(Message(role="assistant", content=text))
#         elif result.action == Action.REQLLM:  # Request LLM to generate a reply after calling the function
#             text = result.result
#             if text is not None and len(text) > 0:
#                 function_id = function_call_data["id"]
#                 function_name = function_call_data["name"]
#                 function_arguments = function_call_data["arguments"]
#                 self.dialogue.put(
#                     Message(
#                         role="assistant",
#                         tool_calls=[
#                             {
#                                 "id": function_id,
#                                 "function": {
#                                     "arguments": "{}" if function_arguments == "" else function_arguments,
#                                     "name": function_name,
#                                 },
#                                 "type": "function",
#                                 "index": 0,
#                             }
#                         ],
#                     )
#                 )

#                 self.dialogue.put(
#                     Message(
#                         role="tool",
#                         tool_call_id=(
#                             str(uuid.uuid4()) if function_id is None else function_id
#                         ),
#                         content=text,
#                     )
#                 )
#                 self.chat(text, tool_call=True, depth=depth + 1)
#         elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
#             text = result.response if result.response else result.result
#             self.tts.tts_one_sentence(
#                 self, ContentType.TEXT, content_detail=text)
#             self.dialogue.put(Message(role="assistant", content=text))
#         else:
#             pass

#     def _report_worker(self):
#         """Chat history reporting worker thread"""
#         while not self.stop_event.is_set():
#             try:
#                 # Get data from the queue, set a timeout to periodically check the stop event
#                 item = self.report_queue.get(timeout=1)
#                 if item is None:  # Detect the poison pill object
#                     break
#                 try:
#                     # Check the thread pool status
#                     if self.executor is None:
#                         continue
#                     # Submit the task to the thread pool
#                     self.executor.submit(self._process_report, *item)
#                 except Exception as e:
#                     self.logger.bind(tag=TAG).error(
#                         f"Chat history reporting thread exception: {e}")
#             except queue.Empty:
#                 continue
#             except Exception as e:
#                 self.logger.bind(tag=TAG).error(
#                     f"Chat history reporting worker thread exception: {e}")

#         self.logger.bind(tag=TAG).info("Chat history reporting thread exited")

#     def _process_report(self, type, text, audio_data, report_time):
#         """Process the reporting task"""
#         try:
#             # Execute the report (pass binary data)
#             report(self, type, text, audio_data, report_time)
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(
#                 f"Report processing exception: {e}")
#         finally:
#             # Mark the task as done
#             self.report_queue.task_done()

#     def clearSpeakStatus(self):
#         self.client_is_speaking = False
#         self.logger.bind(tag=TAG).debug(f"Cleared server speaking status")

#     async def close(self, ws=None):
#         """Resource cleanup method"""
#         try:
#             # Cancel the timeout task
#             if self.timeout_task and not self.timeout_task.done():
#                 self.timeout_task.cancel()
#                 try:
#                     await self.timeout_task
#                 except asyncio.CancelledError:
#                     pass
#                 self.timeout_task = None

#             # Clean up tool handler resources
#             if hasattr(self, "func_handler") and self.func_handler:
#                 try:
#                     await self.func_handler.cleanup()
#                 except Exception as cleanup_error:
#                     self.logger.bind(tag=TAG).error(
#                         f"Error cleaning up tool handler: {cleanup_error}"
#                     )

#             # Trigger the stop event
#             if self.stop_event:
#                 self.stop_event.set()

#             # Clear task queues
#             self.clear_queues()

#             # Close the WebSocket connection
#             try:
#                 if ws:
#                     # Safely check WebSocket state and close
#                     try:
#                         if hasattr(ws, "closed") and not ws.closed:
#                             await ws.close()
#                         elif hasattr(ws, "state") and ws.state.name != "CLOSED":
#                             await ws.close()
#                         else:
#                             # If no closed attribute, try to close directly
#                             await ws.close()
#                     except Exception:
#                         # If closing fails, ignore the error
#                         pass
#                 elif self.websocket:
#                     try:
#                         if (
#                             hasattr(self.websocket, "closed")
#                             and not self.websocket.closed
#                         ):
#                             await self.websocket.close()
#                         elif (
#                             hasattr(self.websocket, "state")
#                             and self.websocket.state.name != "CLOSED"
#                         ):
#                             await self.websocket.close()
#                         else:
#                             # If no closed attribute, try to close directly
#                             await self.websocket.close()
#                     except Exception:
#                         # If closing fails, ignore the error
#                         pass
#             except Exception as ws_error:
#                 self.logger.bind(tag=TAG).error(
#                     f"Error closing WebSocket connection: {ws_error}")

#             if self.tts:
#                 await self.tts.close()

#             # Finally close thread pool (avoid blocking)
#             if self.executor:
#                 try:
#                     self.executor.shutdown(wait=False)
#                 except Exception as executor_error:
#                     self.logger.bind(tag=TAG).error(
#                         f"Error shutting down thread pool: {executor_error}"
#                     )
#                 self.executor = None

#             self.logger.bind(tag=TAG).info("Connection resources released")
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(
#                 f"Error occurred while closing connection: {e}")
#         finally:
#             # Ensure the stop event is set
#             if self.stop_event:
#                 self.stop_event.set()

#     def clear_queues(self):
#         """Clear all task queues"""
#         if self.tts:
#             self.logger.bind(tag=TAG).debug(
#                 f"Starting cleanup: TTS queue size={self.tts.tts_text_queue.qsize()}, audio queue size={self.tts.tts_audio_queue.qsize()}"
#             )

#             # Use non-blocking method to clear queues
#             for q in [
#                 self.tts.tts_text_queue,
#                 self.tts.tts_audio_queue,
#                 self.report_queue,
#             ]:
#                 if not q:
#                     continue
#                 while True:
#                     try:
#                         q.get_nowait()
#                     except queue.Empty:
#                         break

#             self.logger.bind(tag=TAG).debug(
#                 f"Cleanup completed: TTS queue size={self.tts.tts_text_queue.qsize()}, audio queue size={self.tts.tts_audio_queue.qsize()}"
#             )

#     def reset_vad_states(self):
#         self.client_audio_buffer = bytearray()
#         self.client_have_voice = False
#         self.client_voice_stop = False
#         # Reset VAD provider internal states
#         if hasattr(self, 'vad') and self.vad is not None:
#             self.vad.reset()
#         # Clear pre-buffer when resetting VAD states
#         if hasattr(self, 'audio_pre_buffer'):
#             self.audio_pre_buffer.clear()
#         # Clear ASR audio buffer to prevent processing leftover audio
#         if hasattr(self, 'asr_audio'):
#             self.asr_audio.clear()
#         # Clear ASR audio queue for this specific connection only
#         if hasattr(self, 'asr_audio_queue'):
#             # Empty the queue by getting all items without blocking
#             cleared_count = 0
#             while not self.asr_audio_queue.empty():
#                 try:
#                     self.asr_audio_queue.get_nowait()
#                     cleared_count += 1
#                 except queue.Empty:
#                     break
#             if cleared_count > 0:
#                 self.logger.bind(tag=TAG).debug(f"Cleared {cleared_count} audio chunks from ASR queue")
#         self.logger.bind(tag=TAG).info("VAD states reset.")

#     def chat_and_close(self, text):
#         """Chat with the user and then close the connection"""
#         try:
#             # Use the existing chat method
#             self.chat(text)

#             # After chat is complete, close the connection
#             self.close_after_chat = True
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

#     async def _check_timeout(self):
#         """Check for connection timeout"""
#         try:
#             while not self.stop_event.is_set():
#                 # Check for timeout (only if the timestamp has been initialized)
#                 if self.last_activity_time > 0.0:
#                     current_time = time.time() * 1000
#                     if (
#                         current_time - self.last_activity_time
#                         > self.timeout_seconds * 1000
#                     ):
#                         if not self.stop_event.is_set():
#                             self.logger.bind(tag=TAG).info(
#                                 "Connection timed out, preparing to close")
#                             # Set the stop event to prevent duplicate processing
#                             self.stop_event.set()
#                             # Use try-except to wrap the close operation, ensuring no blocking due to exceptions
#                             try:
#                                 await self.close(self.websocket)
#                             except Exception as close_error:
#                                 self.logger.bind(tag=TAG).error(
#                                     f"Error closing connection on timeout: {close_error}"
#                                 )
#                         break
#                 # Check every 10 seconds to avoid being too frequent
#                 await asyncio.sleep(10)
#         except Exception as e:
#             self.logger.bind(tag=TAG).error(f"Timeout check task error: {e}")
#         finally:
#             self.logger.bind(tag=TAG).info("Timeout check task has exited")

import os
import sys
import copy
import json
import uuid
import time
import queue
import asyncio
import threading
import traceback
import subprocess
import websockets
from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from collections import deque
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.providers.tools.unified_tool_handler import UnifiedToolHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, create_connection_logger
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.utils.prompt_manager import PromptManager
from core.utils.voiceprint_provider import VoiceprintProvider
from core.utils import textUtils

TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # Save a reference to the server instance

        self.auth = AuthMiddleware(config)
        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get(
            "read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"

        # Client state related
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"

        # Thread task related
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=5)

        # Add reporting thread pool
        self.report_queue = queue.Queue()
        self.report_thread = None
        # This can be modified in the future to adjust ASR and TTS reporting. Currently, both are enabled by default.
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # Dependent components
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # Manage voiceprint recognition separately for each connection
        self.voiceprint_provider = None

        # VAD related variables
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        # Unified activity timestamp (milliseconds)
        self.last_activity_time = 0.0
        self.client_voice_stop = False
        self.client_voice_window = deque(maxlen=5)
        self.last_is_voice = False

        # ASR related variables
        # Since a public local ASR might be used in actual deployment, variables cannot be exposed to the public ASR.
        # Therefore, variables related to ASR need to be defined here as private variables of the connection.
        self.asr_audio = []
        self.asr_audio_queue = queue.Queue()
        
        # Pre-buffer to store audio chunks before voice detection
        # This helps capture the beginning of speech that might be missed
        self.audio_pre_buffer = deque(maxlen=10)  # Store last 10 chunks (600ms) before voice detection
        
        # Timeout flag for preventing multiple timeout triggers
        self._timeout_triggered = False

        # LLM related variables
        self.llm_finish_task = True
        self.dialogue = Dialogue()

        # TTS related variables
        self.sentence_id = None
        # Handle cases where TTS response has no text
        self.tts_MessageText = ""

        # IoT related variables
        self.iot_descriptors = {}
        self.func_handler = None

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        # Whether to close the connection after the chat ends
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_seconds = (
            int(self.config.get("close_connection_no_voice_time", 120)) + 60
        )  # Add 60 seconds to the original first-level close for a second-level close
        self.timeout_task = None

        # {"mcp":true} indicates that the MCP function is enabled
        self.features = None

        # Initialize prompt manager
        self.prompt_manager = PromptManager(config, self.logger)

    async def handle_connection(self, ws):
        try:
            # Get and validate headers
            self.headers = dict(ws.request.headers)

            if self.headers.get("device-id", None) is None:
                # Try to get device-id from the URL's query parameters
                from urllib.parse import parse_qs, urlparse

                # Get the path from the WebSocket request
                request_path = ws.request.path
                if not request_path:
                    self.logger.bind(tag=TAG).error(
                        "Unable to get request path")
                    return
                parsed_url = urlparse(request_path)
                query_params = parse_qs(parsed_url.query)
                if "device-id" in query_params:
                    self.headers["device-id"] = query_params["device-id"][0]
                    self.headers["client-id"] = query_params["client-id"][0]
                else:
                    await ws.send("Port is normal. To test the connection, please use test_page.html")
                    await self.close(ws)
                    return
            real_ip = self.headers.get("x-real-ip") or self.headers.get(
                "x-forwarded-for"
            )
            if real_ip:
                self.client_ip = real_ip.split(",")[0].strip()
            else:
                self.client_ip = ws.remote_address[0]
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # Perform authentication
            await self.auth.authenticate(self.headers)

            # Authentication passed, continue processing
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)

            # Initialize activity timestamp
            self.last_activity_time = time.time() * 1000

            # Start timeout check task
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id

            # Get differential configuration
            self._initialize_private_config()
            # Asynchronous initialization
            self.executor.submit(self._initialize_components)

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("Client disconnected")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(
                f"Connection error: {str(e)}-{stack_trace}")
            return
        finally:
            try:
                await self._save_and_close(ws)
            except Exception as final_error:
                self.logger.bind(tag=TAG).error(
                    f"Error during final cleanup: {final_error}")
                # Ensure the connection is closed even if saving memory fails
                try:
                    await self.close(ws)
                except Exception as close_error:
                    self.logger.bind(tag=TAG).error(
                        f"Error during forced connection closure: {close_error}"
                    )

    async def _save_and_close(self, ws):
        """Save memory and close the connection"""
        try:
            if self.memory:
                # Log where memory is being saved based on memory type
                memory_type = getattr(self, 'memory_type', 'unknown')
                if memory_type == "nomem":
                    self.logger.bind(tag=TAG).info("Memory saving DISABLED (using nomem)")
                elif memory_type == "mem0ai":
                    self.logger.bind(tag=TAG).info("Saving memory to MEM0 CLOUD")
                elif memory_type == "mem_local_short":
                    self.logger.bind(tag=TAG).info("Saving memory to LOCAL STORAGE (mem_local_short)")
                else:
                    self.logger.bind(tag=TAG).info(f"Saving memory using: {memory_type}")
                
                # Use a thread pool to save memory asynchronously
                def save_memory_task():
                    try:
                        self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Starting memory save task for {memory_type}")
                        self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Dialogue messages count: {len(self.dialogue.dialogue) if self.dialogue and self.dialogue.dialogue else 0}")
                        
                        # Create a new event loop (to avoid conflicts with the main loop)
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Calling memory.save_memory()")
                        result = loop.run_until_complete(
                            self.memory.save_memory(self.dialogue.dialogue)
                        )
                        
                        if result:
                            self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Memory saved successfully using {memory_type}. Result: {result}")
                        else:
                            self.logger.bind(tag=TAG).warning(f"[MEM0-THREAD] Memory save returned None/False for {memory_type}")
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(
                            f"[MEM0-THREAD] Failed to save memory: {e}")
                        self.logger.bind(tag=TAG).error(
                            f"[MEM0-THREAD] Exception traceback: {traceback.format_exc()}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

                # Start a thread to save memory, do not wait for completion
                self.logger.bind(tag=TAG).info(f"[MEM0-THREAD] Starting new thread for memory save")
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to save memory: {e}")
        finally:
            # Close the connection immediately, do not wait for memory saving to complete
            try:
                await self.close(ws)
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"Failed to close connection after saving memory: {close_error}"
                )

    async def _route_message(self, message):
        """Message routing"""
        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None:
                return
            if self.asr is None:
                return
            self.asr_audio_queue.put(message)

    async def handle_restart(self, message):
        """Handle server restart request"""
        try:

            self.logger.bind(tag=TAG).info(
                "Received server restart command, preparing to execute...")

            # Send confirmation response
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "Server restarting...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # Asynchronously execute the restart operation
            def restart_server():
                """The actual method to execute the restart"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("Executing server restart...")
                subprocess.Popen(
                    [sys.executable, "app.py"],
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    start_new_session=True,
                )
                os._exit(0)

            # Use a thread to execute the restart to avoid blocking the event loop
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Restart failed: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            self.logger = create_connection_logger(self.selected_module_str)

            """Initialize components"""
            if self.config.get("prompt") is not None:
                user_prompt = self.config["prompt"]
                # Use a quick prompt for initialization
                prompt = self.prompt_manager.get_quick_prompt(user_prompt)
                self.change_system_prompt(prompt)
                self.logger.bind(tag=TAG).info(
                    f"Quickly initialized component: prompt successful {prompt[:50]}..."
                )

            """Initialize local components"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()

            # Initialize voiceprint recognition
            self._initialize_voiceprint()

            # Open speech recognition channel
            asyncio.run_coroutine_threadsafe(
                self.asr.open_audio_channels(self), self.loop
            )
            if self.tts is None:
                self.tts = self._initialize_tts()
            # Open speech synthesis channel
            asyncio.run_coroutine_threadsafe(
                self.tts.open_audio_channels(self), self.loop
            )

            """Load memory"""
            self._initialize_memory()
            """Load intent recognition"""
            self._initialize_intent()
            """Initialize reporting thread"""
            self._init_report_threads()
            """Update system prompt"""
            self._init_prompt_enhancement()

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to instantiate components: {e}")

    def _init_prompt_enhancement(self):
        # Update context information
        self.prompt_manager.update_context_info(self, self.client_ip)
        enhanced_prompt = self.prompt_manager.build_enhanced_prompt(
            self.config["prompt"], self.device_id, self.client_ip
        )
        if enhanced_prompt:
            self.change_system_prompt(enhanced_prompt)
            self.logger.bind(tag=TAG).info(
                "System prompt has been enhanced and updated")

    def _init_report_threads(self):
        """Initialize ASR and TTS reporting threads"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS reporting thread started")

    def _initialize_tts(self):
        """Initialize TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """Initialize ASR"""
        if self._asr.interface_type == InterfaceType.LOCAL:
            # If the public ASR is a local service, return directly
            # Because one local ASR instance can be shared by multiple connections
            asr = self._asr
        else:
            # If the public ASR is a remote service, initialize a new instance
            # Because a remote ASR involves a WebSocket connection and a receiving thread, each connection needs its own instance
            asr = initialize_asr(self.config)

        return asr

    def _initialize_voiceprint(self):
        """Initialize voiceprint recognition for the current connection"""
        try:
            voiceprint_config = self.config.get("voiceprint", {})
            if voiceprint_config:
                self.voiceprint_provider = VoiceprintProvider(
                    voiceprint_config)
                self.logger.bind(tag=TAG).info(
                    "Voiceprint recognition function dynamically enabled on connection")
            else:
                self.logger.bind(tag=TAG).info(
                    "Voiceprint recognition function not enabled or configuration is incomplete")
        except Exception as e:
            self.logger.bind(tag=TAG).warning(
                f"Voiceprint recognition initialization failed: {str(e)}")

    def _initialize_private_config(self):
        """If getting from the configuration file, perform a second instantiation"""
        if not self.read_config_from_api:
            return
        """Get differential configuration from the interface for a second instantiation, not a full re-instantiation"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(
                self.config.get("delete_audio", True))
            # Log the actual API key status for debugging (without exposing the full key)
            if "Memory" in private_config and "Memory_mem0ai" in private_config.get("Memory", {}):
                mem0_config = private_config["Memory"]["Memory_mem0ai"]
                api_key = mem0_config.get("api_key", "")
                
                # DEBUG: Print the full API key to verify what's being received
                self.logger.bind(tag=TAG).info(f"[DEBUG] Raw mem0 API key received: '{api_key}'")
                
                if api_key == "***":
                    self.logger.bind(tag=TAG).warning(
                        "Mem0 API key is MASKED (***) from manager API - please configure the actual API key in the Manager Web Dashboard under Provider Management"
                    )
                elif api_key:
                    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
                    self.logger.bind(tag=TAG).debug(f"Mem0 API key received: {masked_key} (length: {len(api_key)})")
                else:
                    self.logger.bind(tag=TAG).warning("Mem0 API key is empty in differential configuration")
            
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} seconds, successfully obtained differential configuration: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(
                f"Failed to get differential configuration: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("VLLM", None) is not None:
            self.config["VLLM"] = private_config["VLLM"]
            self.config["selected_module"]["VLLM"] = private_config["selected_module"][
                "VLLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get(
                "selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # Load plugin configuration
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                self.config["plugins"] = plugin_from_server
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = list(plugin_from_server.keys())
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        # Get voiceprint information
        if private_config.get("voiceprint", None) is not None:
            self.config["voiceprint"] = private_config["voiceprint"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(
                private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        if private_config.get("mcp_endpoint", None) is not None:
            self.config["mcp_endpoint"] = private_config["mcp_endpoint"]
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to initialize components: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """Initialize memory module"""
        self.memory.init_memory(
            role_id=self.device_id,
            llm=self.llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # Get memory summary configuration
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # Store memory type for logging
        self.memory_type = memory_type
        
        # If using nomem, return directly
        if memory_type == "nomem":
            self.logger.bind(tag=TAG).info("Memory module initialized: DISABLED (nomem)")
            return
        # Use mem_local_short mode
        elif memory_type == "mem_local_short":
            self.logger.bind(tag=TAG).info("Memory module initialized: LOCAL STORAGE (mem_local_short)")
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # If a dedicated LLM is configured, create an independent LLM instance
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get(
                    "type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"Created a dedicated LLM for memory summary: {memory_llm_name}, type: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # Otherwise use main LLM
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info(
                    "Using main LLM as memory model")
        elif memory_type == "mem0ai":
            self.logger.bind(tag=TAG).info("Memory module initialized: MEM0 CLOUD (mem0ai)")
        else:
            self.logger.bind(tag=TAG).info(f"Memory module initialized: {memory_type}")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """Initialize intent recognition module"""
        # Get intent recognition configuration
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # If using nointent, return directly
        if intent_type == "nointent":
            return
        # Use intent_llm mode
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # If a dedicated LLM is configured, create an independent LLM instance
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get(
                    "type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"Created a dedicated LLM for intent recognition: {intent_llm_name}, type: {intent_llm_type}"
                )
                self.intent.set_llm(intent_llm)
            else:
                # Otherwise use main LLM
                self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info(
                    "Using main LLM as intent recognition model")

        """Load unified tool handler"""
        self.func_handler = UnifiedToolHandler(self)

        # Asynchronously initialize tool handler
        if hasattr(self, "loop") and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.func_handler._initialize(), self.loop)

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # Update system prompt in the context
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, tool_call=False, depth=0):
        self.logger.bind(tag=TAG).info(f"LLM received user message: {query}")
        self.llm_finish_task = False

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Create a new session ID and send a FIRST request for the top-level call
        if depth == 0:
            self.sentence_id = str(uuid.uuid4().hex)
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )

        # Define intent functions
        functions = None
        if self.intent_type == "function_call" and hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        response_message = []

        try:
            # Use dialogue with memory
            memory_str = None
            if self.memory is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            if self.intent_type == "function_call" and functions is not None:
                # Use streaming interface that supports functions
                llm_responses = self.llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(
                        memory_str, self.config.get("voiceprint", {})
                    ),
                    functions=functions,
                )
            else:
                llm_responses = self.llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(
                        memory_str, self.config.get("voiceprint", {})
                    ),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"LLM processing error for '{query}': {e}")
            return None

        # Handle streaming response
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        self.client_abort = False
        emotion_flag = True
        for response in llm_responses:
            if self.client_abort:
                break
            if self.intent_type == "function_call" and functions is not None:
                content, tools_call = response
                if "content" in response:
                    content = response["content"]
                    tools_call = None
                if content is not None and len(content) > 0:
                    content_arguments += content

                if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                    # print("content_arguments", content_arguments)
                    tool_call_flag = True

                if tools_call is not None and len(tools_call) > 0:
                    tool_call_flag = True
                    if tools_call[0].id is not None:
                        function_id = tools_call[0].id
                    if tools_call[0].function.name is not None:
                        function_name = tools_call[0].function.name
                    if tools_call[0].function.arguments is not None:
                        function_arguments += tools_call[0].function.arguments
            else:
                content = response

            # Get emotion from LLM reply, only once at the beginning of a conversation turn
            if emotion_flag and content is not None and content.strip():
                asyncio.run_coroutine_threadsafe(
                    textUtils.get_emotion(self, content),
                    self.loop,
                )
                emotion_flag = False

            if content is not None and len(content) > 0:
                if not tool_call_flag:
                    response_message.append(content)
                    self.tts.tts_text_queue.put(
                        TTSMessageDTO(
                            sentence_id=self.sentence_id,
                            sentence_type=SentenceType.MIDDLE,
                            content_type=ContentType.TEXT,
                            content_detail=content,
                        )
                    )
        # Handle function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                # If the LLM needs to process a turn first, add relevant processed log information
                if len(response_message) > 0:
                    text_buff = "".join(response_message)
                    self.tts_MessageText = text_buff
                    self.dialogue.put(
                        Message(role="assistant", content=text_buff))
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # Use unified tool handler to process all tool calls
                result = asyncio.run_coroutine_threadsafe(
                    self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    ),
                    self.loop,
                ).result()
                self._handle_function_result(
                    result, function_call_data, depth=depth)

        # Store dialogue content
        if len(response_message) > 0:
            text_buff = "".join(response_message)
            self.tts_MessageText = text_buff
            self.dialogue.put(Message(role="assistant", content=text_buff))
        if depth == 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=self.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
        self.llm_finish_task = True
        # Use lambda for delayed calculation, get_llm_dialogue() is only executed at DEBUG level
        self.logger.bind(tag=TAG).debug(
            lambda: json.dumps(
                self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False
            )
        )

        return True

    def _handle_function_result(self, result, function_call_data, depth):
        if result.action == Action.RESPONSE:  # Respond directly to the front-end
            text = result.response
            self.tts.tts_one_sentence(
                self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # Request LLM to generate a reply after calling the function
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": "{}" if function_arguments == "" else function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4()) if function_id is None else function_id
                        ),
                        content=text,
                    )
                )
                self.chat(text, tool_call=True, depth=depth + 1)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.response if result.response else result.result
            self.tts.tts_one_sentence(
                self, ContentType.TEXT, content_detail=text)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _report_worker(self):
        """Chat history reporting worker thread"""
        while not self.stop_event.is_set():
            try:
                # Get data from the queue, set a timeout to periodically check the stop event
                item = self.report_queue.get(timeout=1)
                if item is None:  # Detect the poison pill object
                    break
                try:
                    # Check the thread pool status
                    if self.executor is None:
                        continue
                    # Submit the task to the thread pool
                    self.executor.submit(self._process_report, *item)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(
                        f"Chat history reporting thread exception: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"Chat history reporting worker thread exception: {e}")

        self.logger.bind(tag=TAG).info("Chat history reporting thread exited")

    def _process_report(self, type, text, audio_data, report_time):
        """Process the reporting task"""
        try:
            # Execute the report (pass binary data)
            report(self, type, text, audio_data, report_time)
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Report processing exception: {e}")
        finally:
            # Mark the task as done
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"Cleared server speaking status")

    async def close(self, ws=None):
        """Resource cleanup method"""
        try:
            # Cancel the timeout task
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass
                self.timeout_task = None

            # Clean up tool handler resources
            if hasattr(self, "func_handler") and self.func_handler:
                try:
                    await self.func_handler.cleanup()
                except Exception as cleanup_error:
                    self.logger.bind(tag=TAG).error(
                        f"Error cleaning up tool handler: {cleanup_error}"
                    )

            # Trigger the stop event
            if self.stop_event:
                self.stop_event.set()

            # Clear task queues
            self.clear_queues()

            # Close the WebSocket connection
            try:
                if ws:
                    # Safely check WebSocket state and close
                    try:
                        if hasattr(ws, "closed") and not ws.closed:
                            await ws.close()
                        elif hasattr(ws, "state") and ws.state.name != "CLOSED":
                            await ws.close()
                        else:
                            # If no closed attribute, try to close directly
                            await ws.close()
                    except Exception:
                        # If closing fails, ignore the error
                        pass
                elif self.websocket:
                    try:
                        if (
                            hasattr(self.websocket, "closed")
                            and not self.websocket.closed
                        ):
                            await self.websocket.close()
                        elif (
                            hasattr(self.websocket, "state")
                            and self.websocket.state.name != "CLOSED"
                        ):
                            await self.websocket.close()
                        else:
                            # If no closed attribute, try to close directly
                            await self.websocket.close()
                    except Exception:
                        # If closing fails, ignore the error
                        pass
            except Exception as ws_error:
                self.logger.bind(tag=TAG).error(
                    f"Error closing WebSocket connection: {ws_error}")

            if self.tts:
                await self.tts.close()

            # Finally close thread pool (avoid blocking)
            if self.executor:
                try:
                    self.executor.shutdown(wait=False)
                except Exception as executor_error:
                    self.logger.bind(tag=TAG).error(
                        f"Error shutting down thread pool: {executor_error}"
                    )
                self.executor = None

            self.logger.bind(tag=TAG).info("Connection resources released")
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Error occurred while closing connection: {e}")
        finally:
            # Ensure the stop event is set
            if self.stop_event:
                self.stop_event.set()

    def clear_queues(self):
        """Clear all task queues"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"Starting cleanup: TTS queue size={self.tts.tts_text_queue.qsize()}, audio queue size={self.tts.tts_audio_queue.qsize()}"
            )

            # Use non-blocking method to clear queues
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            self.logger.bind(tag=TAG).debug(
                f"Cleanup completed: TTS queue size={self.tts.tts_text_queue.qsize()}, audio queue size={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        # Reset VAD provider internal states
        if hasattr(self, 'vad') and self.vad is not None:
            self.vad.reset()
        # Clear pre-buffer when resetting VAD states
        if hasattr(self, 'audio_pre_buffer'):
            self.audio_pre_buffer.clear()
        # Clear ASR audio buffer to prevent processing leftover audio
        if hasattr(self, 'asr_audio'):
            self.asr_audio.clear()
        # Reset VAD recording start time for timeout
        if hasattr(self, 'vad_recording_start_time'):
            self.vad_recording_start_time = None
        # Reset timeout flag
        if hasattr(self, '_timeout_triggered'):
            self._timeout_triggered = False
        # Also reset listen start time to prevent conflicts
        if hasattr(self, 'listen_start_time'):
            self.listen_start_time = None
        # Clear ASR audio queue for this specific connection only
        if hasattr(self, 'asr_audio_queue'):
            # Empty the queue by getting all items without blocking
            cleared_count = 0
            while not self.asr_audio_queue.empty():
                try:
                    self.asr_audio_queue.get_nowait()
                    cleared_count += 1
                except queue.Empty:
                    break
            if cleared_count > 0:
                self.logger.bind(tag=TAG).debug(f"Cleared {cleared_count} audio chunks from ASR queue")
        self.logger.bind(tag=TAG).info("VAD states reset.")

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """Check for connection timeout"""
        try:
            while not self.stop_event.is_set():
                # Check for timeout (only if the timestamp has been initialized)
                if self.last_activity_time > 0.0:
                    current_time = time.time() * 1000
                    if (
                        current_time - self.last_activity_time
                        > self.timeout_seconds * 1000
                    ):
                        if not self.stop_event.is_set():
                            self.logger.bind(tag=TAG).info(
                                "Connection timed out, preparing to close")
                            # Set the stop event to prevent duplicate processing
                            self.stop_event.set()
                            # Use try-except to wrap the close operation, ensuring no blocking due to exceptions
                            try:
                                await self.close(self.websocket)
                            except Exception as close_error:
                                self.logger.bind(tag=TAG).error(
                                    f"Error closing connection on timeout: {close_error}"
                                )
                        break
                # Check every 10 seconds to avoid being too frequent
                await asyncio.sleep(10)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Timeout check task error: {e}")
        finally:
            self.logger.bind(tag=TAG).info("Timeout check task has exited")
