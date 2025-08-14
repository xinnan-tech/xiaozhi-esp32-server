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
        # Add cache management
        self.intent_cache = {}  # Cache for intent recognition results
        self.cache_expiry = 600  # Cache validity period of 10 minutes
        self.cache_max_size = 100  # Maximum of 100 intents to cache
        self.history_count = 4  # Default to using the last 4 conversation records

    def get_intent_system_prompt(self, functions_list: str) -> str:
        """
        Dynamically generate a system prompt based on configured intent options and available functions.
        Args:
            functions: A list of available functions in JSON format string.
        Returns:
            A formatted system prompt.
        """

        # Build the function description part
        functions_desc = "Available functions list:\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\nFunction Name: {name}\n"
            functions_desc += f"Description: {desc}\n"

            if params:
                functions_desc += "Parameters:\n"
                for param_name, param_info in params.get("properties", {}).items():
                    param_desc = param_info.get("description", "")
                    param_type = param_info.get("type", "")
                    functions_desc += f"- {param_name} ({param_type}): {param_desc}\n"

            functions_desc += "---\n"

        prompt = (
            "You are an intent recognition assistant. Please analyze the user's last sentence to determine the user's intent and call the corresponding function.\n\n"
            "- If the user uses question words (like 'how', 'why', 'what') to ask about exiting (e.g., 'How did it exit?'), note that this is not a request to exit. Please return {'function_call': {'name': 'continue_chat'}}\n"
            "- Only trigger handle_exit_intent when the user explicitly uses commands like 'exit system', 'end conversation', 'I don't want to talk to you anymore'.\n\n"
            f"{functions_desc}\n"
            "Processing Steps:\n"
            "1. Analyze user input to determine user intent.\n"
            "2. Select the best matching function from the list of available functions.\n"
            "3. If a matching function is found, generate the corresponding function_call format.\n"
            '4. If no matching function is found, return {"function_call": {"name": "continue_chat"}}\n\n'
            "Return Format Requirements:\n"
            "1. Must return in pure JSON format.\n"
            "2. Must include the function_call field.\n"
            "3. function_call must include the name field.\n"
            "4. If the function requires parameters, it must include the arguments field.\n\n"
            "Examples:\n"
            "```\n"
            "User: What time is it?\n"
            'Return: {"function_call": {"name": "get_time"}}\n'
            "```\n"
            "```\n"
            "User: What is the current battery level?\n"
            'Return: {"function_call": {"name": "get_battery_level", "arguments": {"response_success": "Current battery level is {value}%", "response_failure": "Unable to get the current battery percentage."}}}\n'
            "```\n"
            "```\n"
            "User: What is the current screen brightness?\n"
            'Return: {"function_call": {"name": "self_screen_get_brightness"}}\n'
            "```\n"
            "```\n"
            "User: Set screen brightness to 50%.\n"
            'Return: {"function_call": {"name": "self_screen_set_brightness", "arguments": {"brightness": 50}}}\n'
            "```\n"
            "```\n"
            "User: I want to end the conversation.\n"
            'Return: {"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "goodbye"}}}\n'
            "```\n"
            "```\n"
            "User: Hello.\n"
            'Return: {"function_call": {"name": "continue_chat"}}\n'
            "```\n\n"
            "Note:\n"
            "1. Only return in JSON format, do not include any other text.\n"
            '2. If no matching function is found, return {"function_call": {"name": "continue_chat"}}.\n'
            "3. Ensure the returned JSON format is correct and includes all necessary fields.\n"
            "Special Instructions:\n"
            "- When a single user input contains multiple commands (e.g., 'turn on the light and increase the volume').\n"
            "- Please return a JSON array of multiple function_calls.\n"
            "- Example: {'function_calls': [{'name':'light_on'}, {'name':'volume_up'}]}"
        )
        return prompt

    def clean_cache(self):
        """Clean up expired cache."""
        now = time.time()
        # Find expired keys
        expired_keys = [
            k
            for k, v in self.intent_cache.items()
            if now - v["timestamp"] > self.cache_expiry
        ]
        for key in expired_keys:
            del self.intent_cache[key]

        # If the cache is too large, remove the oldest entries
        if len(self.intent_cache) > self.cache_max_size:
            # Sort by timestamp and keep the newest entries
            sorted_items = sorted(
                self.intent_cache.items(), key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_items[: len(sorted_items) - self.cache_max_size]:
                del self.intent_cache[key]

    def replyResult(self, text: str, original_text: str):
        llm_result = self.llm.response_no_stream(
            system_prompt=text,
            user_prompt="Based on the content above, please reply to the user in a human-like tone, keep it concise, and return the result directly. The user now says: "
            + original_text,
        )
        return llm_result

    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # Record the overall start time
        total_start_time = time.time()

        # Print the model information being used
        model_info = getattr(self.llm, "model_name",
                             str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(
            f"Using intent recognition model: {model_info}")

        # Calculate the cache key
        cache_key = hashlib.md5(text.encode()).hexdigest()

        # Check the cache
        if cache_key in self.intent_cache:
            cache_entry = self.intent_cache[cache_key]
            # Check if the cache has expired
            if time.time() - cache_entry["timestamp"] <= self.cache_expiry:
                cache_time = time.time() - total_start_time
                logger.bind(tag=TAG).debug(
                    f"Using cached intent: {cache_key} -> {cache_entry['intent']}, time taken: {cache_time:.4f} seconds"
                )
                return cache_entry["intent"]

        # Clean the cache
        self.clean_cache()

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
            hass_prompt = "\nHere is a list of my smart home devices (location, device name, entity_id), which can be controlled via Home Assistant:\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # Build the user dialogue history prompt
        msgStr = ""

        # Get the recent dialogue history
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            msgStr += f"{dialogue_history[i].role}: {dialogue_history[i].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # Record the preprocessing completion time
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"Intent recognition preprocessing time: {preprocess_time:.4f} seconds")

        # Use LLM for intent recognition
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(
            f"Starting LLM intent recognition call, model: {model_info}")

        intent = self.llm.response_no_stream(
            system_prompt=prompt_music, user_prompt=user_prompt
        )

        # Record the LLM call completion time
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"LLM intent recognition complete, model: {model_info}, call time: {llm_time:.4f} seconds"
        )

        # Record the post-processing start time
        postprocess_start_time = time.time()

        # Clean and parse the response
        intent = intent.strip()
        # Try to extract the JSON part
        match = re.search(r"\{.*\}", intent, re.DOTALL)
        if match:
            intent = match.group(0)

        # Record the total processing time
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"【Intent Recognition Performance】Model: {model_info}, Total time: {total_time:.4f}s, LLM call: {llm_time:.4f}s, Query: '{text[:20]}...'"
        )

        # Try to parse as JSON
        try:
            intent_data = json.loads(intent)
            # If it contains function_call, format it for processing
            if "function_call" in intent_data:
                function_data = intent_data["function_call"]
                function_name = function_data.get("name")
                function_args = function_data.get("arguments", {})

                # Record the recognized function call
                logger.bind(tag=TAG).info(
                    f"LLM recognized intent: {function_name}, arguments: {function_args}"
                )

                # If continuing the chat, clean up tool call related history messages
                if function_name == "continue_chat":
                    # Keep non-tool related messages
                    clean_history = [
                        msg
                        for msg in conn.dialogue.dialogue
                        if msg.role not in ["tool", "function"]
                    ]
                    conn.dialogue.dialogue = clean_history

                # Add to cache
                self.intent_cache[cache_key] = {
                    "intent": intent,
                    "timestamp": time.time(),
                }

                # Post-processing time
                postprocess_time = time.time() - postprocess_start_time
                logger.bind(tag=TAG).debug(
                    f"Intent post-processing time: {postprocess_time:.4f} seconds")

                # Ensure a fully serialized JSON string is returned
                return intent
            else:
                # Add to cache
                self.intent_cache[cache_key] = {
                    "intent": intent,
                    "timestamp": time.time(),
                }

                # Post-processing time
                postprocess_time = time.time() - postprocess_start_time
                logger.bind(tag=TAG).debug(
                    f"Intent post-processing time: {postprocess_time:.4f} seconds")

                # Return normal intent
                return intent
        except json.JSONDecodeError:
            # Post-processing time
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).error(
                f"Failed to parse intent JSON: {intent}, post-processing time: {postprocess_time:.4f} seconds"
            )
            # If parsing fails, default to returning a continue chat intent
            return '{"intent": "Continue Chat"}'
