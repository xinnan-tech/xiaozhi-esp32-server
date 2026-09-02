from typing import List, Dict
from ..base import IntentProviderBase
from plugins_func.functions.play_music import initialize_music_handler
from config.logger import setup_logging
import re
import json
import hashlib
import time

TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.promot = ""
        # Import global cache manager
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType
        self.history_count = 4  # Default to using the last 4 dialogue records

    def get_intent_system_prompt(self, functions_list: list) -> str:
        """
        Dynamically generate a concise English system prompt for intent recognition.
        """
        # Build tool description section
        functions_desc = "AVAILABLE TOOLS:\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\n- {name}: {desc}\n"
            if params:
                props = params.get("properties", {})
                for p_name, p_info in props.items():
                    functions_desc += f"  * {p_name} ({p_info.get('type')}): {p_info.get('description')}\n"

        prompt = (
            "You are a strict code interpreter. Your ONLY job is to route user input to a tool.\n"
            "OUTPUT valid JSON ONLY. NO explanation.\n\n"
            "TOOLS:\n"
            f"{functions_desc}\n"
            "MAPPING RULES:\n"
            "1. WEATHER -> 'get_weather'\n"
            "2. LOCATION -> 'get_location'\n"
            "3. TIME/DATE -> {'function_call': {'name': 'result_for_context'}}\n"
            "4. CHANGE HARDWARE (Volume, Brightness, Theme) -> 'self_*' tool\n"
            "5. GET HARDWARE STATUS (Battery, Volume, Wifi, etc.) -> 'self_get_device_status'\n"
            "6. TAKE PHOTO/VISION -> 'self_camera_take_photo'\n"
            "7. GENERAL KNOWLEDGE (e.g. Science, History) -> {'function_call': {'name': 'continue_chat'}}\n"
            "8. OTHER -> {'function_call': {'name': 'continue_chat'}}\n\n"
            "EXAMPLES:\n"
            "User: Hello\n"
            "{\"function_call\": {\"name\": \"continue_chat\"}}\n\n"
            "User: What is your battery level?\n"
            "{\"function_call\": {\"name\": \"self_get_device_status\"}}\n\n"
            "User: Is the wifi connected?\n"
            "{\"function_call\": {\"name\": \"self_get_device_status\"}}\n\n"
            "User: Weather in Tokyo?\n"
            "{\"function_call\": {\"name\": \"get_weather\", \"arguments\": {\"location\": \"Tokyo\"}}}\n\n"
            "User: Volume up\n"
            "{\"function_call\": {\"name\": \"self_audio_speaker_set_volume\", \"arguments\": {\"volume\": 80}}}\n\n"
            "User: Set brightness to 50%\n"
            "{\"function_call\": {\"name\": \"self_screen_set_brightness\", \"arguments\": {\"brightness\": 50}}}\n\n"
            "User: Take a photo of this\n"
            "{\"function_call\": {\"name\": \"self_camera_take_photo\", \"arguments\": {\"question\": \"Describe this photo\"}}}\n\n"
            "User: Who won the game?\n"
            "{\"function_call\": {\"name\": \"continue_chat\"}}\n"
            "User: Okay, thanks\n"
            "{\"function_call\": {\"name\": \"continue_chat\"}}\n"
            "User: Where are we?\n"
            "{\"function_call\": {\"name\": \"get_location\"}}\n"
        )
        return prompt

    def replyResult(self, text: str, original_text: str):
        llm_result = self.llm.response_no_stream(
            system_prompt=text,
            user_prompt="Based on the above, reply to the user in a human-like tone. Be concise and return the result directly. The user says: "
            + original_text,
        )
        return llm_result

    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # Record total start time
        total_start_time = time.time()

        # Print model info
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"Using intent model: {model_info}")

        # Calculate cache key
        cache_key = hashlib.md5((conn.device_id + text).encode()).hexdigest()

        # Check cache
        cached_intent = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached_intent is not None:
            cache_time = time.time() - total_start_time
            logger.bind(tag=TAG).debug(
                f"Using cached intent: {cache_key} -> {cached_intent}, Time: {cache_time:.4f}s"
            )
            return cached_intent

        if self.promot == "":
            functions = conn.func_handler.get_functions()
            if hasattr(conn, "mcp_client"):
                mcp_tools = conn.mcp_client.get_available_tools()
                if mcp_tools is not None and len(mcp_tools) > 0:
                    if functions is None:
                        functions = []
                    functions.extend(mcp_tools)

            self.promot = self.get_intent_system_prompt(functions)

        music_config = initialize_music_handler(conn)
        music_file_names = music_config["music_file_names"]
        prompt_music = f"{self.promot}\n<musicNames>{music_file_names}\n</musicNames>"

        home_assistant_cfg = conn.config["plugins"].get("home_assistant")
        if home_assistant_cfg:
            devices = home_assistant_cfg.get("devices", [])
        else:
            devices = []
        if len(devices) > 0:
            hass_prompt = "\nHere is my list of smart devices (location, device name, entity_id), which can be controlled via Home Assistant\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # Build user dialogue history prompt
        msgStr = ""

        # Get recent dialogue history
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            msgStr += f"{dialogue_history[i].role}: {dialogue_history[i].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # Record preprocessing completion time
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(f"Intent preprocessing time: {preprocess_time:.4f}s")

        # Use LLM for intent recognition
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(f"Start LLM intent call, model: {model_info}")

        intent = self.llm.response_no_stream(
            system_prompt=prompt_music, user_prompt=user_prompt, response_format={"type": "json_object"}
        )

        # Record LLM call completion time
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"External LLM intent completed, model: {model_info}, Time: {llm_time:.4f}s"
        )

        # Record post-processing start time
        postprocess_start_time = time.time()

        # Clean and parse response
        intent = intent.strip()
        # Try to extract JSON part
        match = re.search(r"\{.*\}", intent, re.DOTALL)
        if match:
            intent = match.group(0)

        # Record total processing time
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"[Intent Performance] Model: {model_info}, Total: {total_time:.4f}s, LLM: {llm_time:.4f}s, Query: '{text[:20]}...'"
        )

        # Try to parse as JSON
        try:
            intent_data = json.loads(intent)
        except json.JSONDecodeError:
            # Fallback regex parsing
            logger.bind(tag=TAG).warning(f"JSON extract failed for: {intent}, attempting regex fallback")
            
            # Try to find function name
            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', intent)
            if not name_match:
                 # Try to find name without quotes if model is very broken
                name_match = re.search(r'name\s*:\s*"([^"]+)"', intent)
            
            if name_match:
                func_name = name_match.group(1)
                args = {}
                # Try to find simple arguments
                # This is a very basic extraction
                args_match = re.search(r'"arguments"\s*:\s*({[^}]+})', intent)
                if args_match:
                    try:
                        args = json.loads(args_match.group(1))
                    except:
                        pass
                
                intent_data = {
                    "function_call": {
                        "name": func_name,
                        "arguments": args
                    }
                }
                logger.bind(tag=TAG).info(f"Regex recovery successful: {func_name}")
            else:
                 postprocess_time = time.time() - postprocess_start_time
                 logger.bind(tag=TAG).error(
                    f"Cannot parse intent JSON: {intent}, Post-process time: {postprocess_time:.4f}s"
                 )
                 return '{"function_call": {"name": "continue_chat"}}'

        # If it contains function_call, format it for processing
        if "function_call" in intent_data:
            function_data = intent_data["function_call"]
            function_name = function_data.get("name")
            function_args = function_data.get("arguments", {})

            # Record identified function call
            logger.bind(tag=TAG).info(
                f"LLM identified intent: {function_name}, args: {function_args}"
            )

            # Handle different types of intents
            if function_name == "result_for_context":
                # Handle basic info query, answer directly from context
                logger.bind(tag=TAG).info(
                    "Detected result_for_context intent, answering directly from context"
                )

            elif function_name == "continue_chat":
                # Handle normal chat
                # Keep non-tool related messages
                clean_history = [
                    msg
                    for msg in conn.dialogue.dialogue
                    if msg.role not in ["tool", "function"]
                ]
                conn.dialogue.dialogue = clean_history

            else:
                # Handle function call
                logger.bind(tag=TAG).info(f"Detected function call intent: {function_name}")

        # Unified cache processing and return
        # Re-dump to ensure valid JSON string is returned even if we repaired it
        final_intent_str = json.dumps(intent_data)

        # Log the entire JSON structure if it's a function call (MCP request)
        if "function_call" in intent_data:
            logger.bind(tag=TAG).info(f"Intent LLM Response: {final_intent_str}")
        
        self.cache_manager.set(self.CacheType.INTENT, cache_key, final_intent_str)
        postprocess_time = time.time() - postprocess_start_time
        logger.bind(tag=TAG).debug(f"Intent post-processing time: {postprocess_time:.4f}s")
        return final_intent_str
