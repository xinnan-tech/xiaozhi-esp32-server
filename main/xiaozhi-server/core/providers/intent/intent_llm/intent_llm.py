import asyncio
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import IntentProviderBase
from plugins_func.functions.play_music import initialize_music_handler
from config.logger import setup_logging
from core.utils.util import get_system_error_response
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
        # Import the shared cache manager.
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType
        self.history_count = 4  # Use the latest four dialogue entries by default.

    def get_intent_system_prompt(self, functions_list: str) -> str:
        """
        Build the intent-detection system prompt from the configured options and
        available functions.

        Args:
            functions: Available functions as a JSON-like list.

        Returns:
            Formatted system prompt text.
        """

        # Build the function reference section.
        functions_desc = "Available functions:\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\nFunction name: {name}\n"
            functions_desc += f"Description: {desc}\n"

            if params:
                functions_desc += "Parameters:\n"
                for param_name, param_info in params.get("properties", {}).items():
                    param_desc = param_info.get("description", "")
                    param_type = param_info.get("type", "")
                    functions_desc += f"- {param_name} ({param_type}): {param_desc}\n"

            functions_desc += "---\n"

        prompt = (
            "[Strict output format] You must return JSON only. Do not return any natural language.\n\n"
            "You are an intent-detection assistant. Analyze the user's latest message, determine the intent, and choose the matching function.\n\n"
            "[Important rules] Return `result_for_context` directly for the following kinds of queries without calling any other function:\n"
            "- Asking for the current time (for example: what time is it, current time, check the time)\n"
            "- Asking for today's date (for example: what day is it, what date is today, what weekday is today)\n"
            "- Asking for today's standard calendar information already present in context\n"
            "- Asking which city the user is currently in (for example: where am I now, do you know which city I'm in)\n"
            "The system will build the answer directly from contextual information.\n\n"
            "- If the user uses question words such as 'how', 'why', or 'what happened' to ask about exiting (for example, 'why did it exit?'), this is not an exit command. Return {'function_call': {'name': 'continue_chat'}}.\n"
            "- Trigger `handle_exit_intent` only when the user clearly says things like 'exit the system', 'end the conversation', or 'I don't want to talk anymore'.\n\n"
            f"{functions_desc}\n"
            "Process:\n"
            "1. Analyze the user input and determine the intent.\n"
            "2. Check whether it is one of the basic-context queries above. If it is, return `result_for_context`.\n"
            "3. Choose the best matching function from the available function list.\n"
            "4. If a matching function exists, generate the matching `function_call` payload.\n"
            '5. If no matching function exists, return {"function_call": {"name": "continue_chat"}}.\n\n'
            "Response format requirements:\n"
            "1. Return pure JSON only, with no extra text.\n"
            "2. Include a `function_call` field.\n"
            "3. `function_call` must include `name`.\n"
            "4. If a function needs parameters, include an `arguments` field.\n\n"
            "Examples:\n"
            "```\n"
            "User: What time is it now?\n"
            'Return: {"function_call": {"name": "result_for_context"}}\n'
            "```\n"
            "```\n"
            "User: What is the current battery level?\n"
            'Return: {"function_call": {"name": "get_battery_level", "arguments": {"response_success": "The current battery level is {value}%.", "response_failure": "Unable to retrieve the current battery percentage."}}}\n'
            "```\n"
            "```\n"
            "User: What is the current screen brightness?\n"
            'Return: {"function_call": {"name": "self_screen_get_brightness"}}\n'
            "```\n"
            "```\n"
            "User: Set the screen brightness to 50%.\n"
            'Return: {"function_call": {"name": "self_screen_set_brightness", "arguments": {"brightness": 50}}}\n'
            "```\n"
            "```\n"
            "User: I want to end the conversation.\n"
            'Return: {"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "goodbye"}}}\n'
            "```\n"
            "```\n"
            "User: Hi there.\n"
            'Return: {"function_call": {"name": "continue_chat"}}\n'
            "```\n\n"
            "Notes:\n"
            "1. Return JSON only, with no extra words.\n"
            '2. Prioritize checking for basic context queries first. If matched, return {"function_call": {"name": "result_for_context"}} with no arguments.\n'
            '3. If no matching function exists, return {"function_call": {"name": "continue_chat"}}.\n'
            "4. Make sure the JSON is valid and contains all required fields.\n"
            "5. `result_for_context` does not need arguments; the system will pull the needed context automatically.\n"
            "Special case:\n"
            "- When a single user message includes multiple commands (for example, 'turn on the light and raise the volume'),\n"
            "- return a JSON array containing multiple function calls.\n"
            "- Example: {'function_calls': [{name:'light_on'}, {name:'volume_up'}]}\n\n"
            "[Final warning] Never output natural language, emoji, or explanations. Output valid JSON only."
        )
        return prompt

    async def replyResult(self, text: str, original_text: str):
        """使用 asyncio.to_thread 避免阻塞事件循环"""
        try:
            user_prompt = (
                "请根据以上内容，像人类一样说话的口吻回复用户，要求简洁，请直接返回结果。用户现在说："
                + original_text
            )
            # 使用 to_thread 将同步阻塞调用放到线程池中执行，不阻塞事件循环
            llm_result = await asyncio.to_thread(
                self.llm.response_no_stream,
                system_prompt=text,
                user_prompt="Based on the information above, reply in a natural human tone. Be concise and return only the answer. The user now says: "
                + original_text,
            )
            return llm_result
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in generating reply result: {e}")
            return get_system_error_response(self.config)

    async def detect_intent(
        self, conn: "ConnectionHandler", dialogue_history: List[Dict], text: str
    ) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # Track the overall start time.
        total_start_time = time.time()

        # Log the model being used.
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"Using intent-detection model: {model_info}")

        # Build the cache key.
        cache_key = hashlib.md5((conn.device_id + text).encode()).hexdigest()

        # Check the cache first.
        cached_intent = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached_intent is not None:
            cache_time = time.time() - total_start_time
            logger.bind(tag=TAG).debug(
                f"Using cached intent: {cache_key} -> {cached_intent}, elapsed: {cache_time:.4f}s"
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
            hass_prompt = "\nHere is the list of smart home devices (location, device name, entity_id) that can be controlled through Home Assistant:\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # Build the prompt from recent dialogue history.
        msgStr = ""

        # Use only the most recent dialogue history window.
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            msgStr += f"{dialogue_history[i].role}: {dialogue_history[i].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # Log preprocessing time.
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"Intent preprocessing time: {preprocess_time:.4f}s"
        )

        # Run the LLM for intent detection.
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(
            f"Starting LLM intent-detection call with model: {model_info}"
        )

        try:
            # 使用 to_thread 将同步阻塞调用放到线程池中，避免阻塞事件循环
            intent = await asyncio.to_thread(
                self.llm.response_no_stream,
                system_prompt=prompt_music,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in intent detection LLM call: {e}")
            return '{"function_call": {"name": "continue_chat"}}'

        # Log LLM call time.
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"External LLM intent detection finished. Model: {model_info}, call time: {llm_time:.4f}s"
        )

        # Start post-processing.
        postprocess_start_time = time.time()

        # Clean and parse the response.
        intent = intent.strip()
        # Try to extract the JSON object.
        match = re.search(r"\{.*\}", intent, re.DOTALL)
        if match:
            intent = match.group(0)

        # Log total processing time.
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"[Intent detection performance] Model: {model_info}, total time: {total_time:.4f}s, LLM time: {llm_time:.4f}s, query: '{text[:20]}...'"
        )

        # Parse the JSON result.
        try:
            intent_data = json.loads(intent)
            # Normalize function-call payloads for downstream handling.
            if "function_call" in intent_data:
                function_data = intent_data["function_call"]
                function_name = function_data.get("name")
                function_args = function_data.get("arguments", {})

                # Record the detected function call.
                logger.bind(tag=TAG).info(
                    f"LLM detected intent: {function_name}, arguments: {function_args}"
                )

                # Handle the recognized intent type.
                if function_name == "result_for_context":
                    # Handle context-backed queries directly.
                    logger.bind(tag=TAG).info(
                        "Detected result_for_context intent; the system will answer directly from context"
                    )

                elif function_name == "continue_chat":
                    # Handle regular dialogue by removing tool-only messages.
                    clean_history = [
                        msg
                        for msg in conn.dialogue.dialogue
                        if msg.role not in ["tool", "function"]
                    ]
                    conn.dialogue.dialogue = clean_history

                else:
                    # Handle an explicit function call intent.
                    logger.bind(tag=TAG).info(
                        f"Detected function-call intent: {function_name}"
                    )

            # Cache and return the normalized result.
            self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).debug(
                f"Intent post-processing time: {postprocess_time:.4f}s"
            )
            return intent
        except json.JSONDecodeError:
            # Fall back to continue_chat if parsing fails.
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).error(
                f"Unable to parse intent JSON: {intent}, post-processing time: {postprocess_time:.4f}s"
            )
            return '{"function_call": {"name": "continue_chat"}}'
