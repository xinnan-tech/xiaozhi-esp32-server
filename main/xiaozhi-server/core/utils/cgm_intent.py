"""
Context Intent Classifier

Uses the fast intent LLM to determine:
1. Which context (CGM, Pump, News) should be injected
2. If a query can be answered directly (time, weather, location, volume, brightness, battery)
3. Whether a diabetes question needs CGM context, pump context, or both

This is a purely LLM-driven classifier for multilingual support.
"""
import json
import hashlib
import time
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from config.logger import setup_logging
from core.utils import llm as llm_utils

TAG = __name__
logger = setup_logging()

# Global singleton for the classifier
_classifier = None


class ContextIntentClassifier:
    """Fast classifier to determine context needs and control signals."""
    
    SYSTEM_PROMPT = """You are a speed-optimized Intent Classifier. Output ONLY JSON.
CRITICAL: Use the user's language for 'reply' and 'search_query'.
IMPORTANT: Put "fast_answer" FIRST in the JSON.

Schema:
{"fast_answer": "time"|"weather"|"location"|"exit"|"volume"|"brightness"|"battery"|null, "language": "English"|"Chinese", "needs_cgm": bool, "needs_pump": bool, "needs_news": bool, "needs_search": bool, "search_query": string|null, "reply": string}

Behavior Rules:
1. 'weather' -> If user asks for current weather, set "fast_answer": "weather" (internal plugin).
2. 'battery' -> If user asks for battery or power, set "fast_answer": "battery".
3. 'volume' -> If user asks about volume level, set "fast_answer": "volume".
4. 'time' -> If user asks the current time, set "fast_answer": "time".
5. 'location' -> If user asks where they are or current location, set "fast_answer": "location".
6. 'search_query' -> MUST be in the user's language.
7. NO SEARCH for Chat -> Greetings ("how are you", "hello"), compliments ("you are great"), or philosophical questions must NOT trigger 'needs_search'. Leave search_query null and needs_search false.
8. NO REDUNDANT SEARCH -> If information (news, headlines, weather) is already present in the history or current context, set 'needs_search' to false. Only search if the information is missing or outdated.
9. NO SEARCH for Meta-Chat -> Questions about your own features, hardware capabilities, previous turns ("why didn't you answer"), or your "internal state" must NOT trigger 'needs_search'.
10. 'needs_cgm' -> Set true when the user asks about glucose, blood sugar, readings, trends, highs, lows, time in range, glycemic control, patterns, current glucose, or diabetes status inferred from CGM.
11. 'needs_pump' -> Set true when the user asks about insulin, bolus, basal, temp basal, carb ratio, correction, pump activity, pump profile, insulin effectiveness, or pump-delivered events.
12. Set BOTH 'needs_cgm' and 'needs_pump' to true when the question requires joint reasoning, such as insulin response, whether a bolus worked, post-meal control, correction effectiveness, or overall diabetes management using both glucose and pump data.
13. 'needs_news' -> Set true only for explicit news/headlines/current events requests.
14. For ordinary diabetes coaching or status questions, do NOT set 'needs_search' unless the user is explicitly asking for external knowledge, public information, or recent news.
15. 'reply' -> A short natural response in the user's language.

Examples:
- "how's the weather" -> {"fast_answer": "weather", "language": "English", "needs_cgm": false, "needs_pump": false, "needs_news": false, "needs_search": false, "search_query": null, "reply": "Checking the weather for you."}
- "how are you" -> {"fast_answer": null, "language": "English", "needs_cgm": false, "needs_pump": false, "needs_news": false, "needs_search": false, "search_query": null, "reply": "I'm doing great, thanks for asking!"}
- "who is Steve Jobs" -> {"fast_answer": null, "language": "English", "needs_cgm": false, "needs_pump": false, "needs_news": false, "needs_search": true, "search_query": "who is Steve Jobs", "reply": "Searching for Steve Jobs..."}
- "current volume" -> {"fast_answer": "volume", "language": "English", "needs_cgm": false, "needs_pump": false, "needs_news": false, "needs_search": false, "search_query": null, "reply": "Checking the current volume level..."}
- "How is my glucose today?" -> {"fast_answer": null, "language": "English", "needs_cgm": true, "needs_pump": false, "needs_news": false, "needs_search": false, "search_query": null, "reply": "Let me check your recent glucose data."}
- "Did my last bolus work?" -> {"fast_answer": null, "language": "English", "needs_cgm": true, "needs_pump": true, "needs_news": false, "needs_search": false, "search_query": null, "reply": "Let me check your recent insulin and glucose response."}
- "最近胰岛素有没有起作用" -> {"fast_answer": null, "language": "Chinese", "needs_cgm": true, "needs_pump": true, "needs_news": false, "needs_search": false, "search_query": null, "reply": "我来看看你最近的胰岛素和血糖反应。"}
- "最近血糖控制怎么样" -> {"fast_answer": null, "language": "Chinese", "needs_cgm": true, "needs_pump": false, "needs_news": false, "needs_search": false, "search_query": null, "reply": "我来看看你最近的血糖情况。"}
- "最近pump有没有异常" -> {"fast_answer": null, "language": "English", "needs_cgm": false, "needs_pump": true, "needs_news": false, "needs_search": false, "search_query": null, "reply": "Let me check your recent pump activity."}
"""

    def __init__(self, config):
        self.config = config
        self.llm = None
        self._init_llm()
        
        # Cache for intent results
        from core.utils.cache.manager import cache_manager, CacheType
        self.cache_manager = cache_manager
        self.CacheType = CacheType
    
    def _init_llm(self):
        """Initialize the fast intent LLM."""
        try:
            llm_config = self.config.get("LLM", {})
            if "fast_intent" in llm_config:
                fast_config = llm_config["fast_intent"]
                llm_type = fast_config.get("type", "openai")
                self.llm = llm_utils.create_instance(llm_type, fast_config)
            else:
                main_llm_name = self.config.get("selected_module", {}).get("LLM", "openai")
                if main_llm_name in llm_config:
                    main_config = llm_config[main_llm_name]
                    llm_type = main_config.get("type", "openai")
                    self.llm = llm_utils.create_instance(llm_type, main_config)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize context classifier LLM: {e}")
            self.llm = None
    
    def classify(self, query: str, client_id: str, language_hint: str = None) -> dict:
        """Classify what context is needed and if fast answer is available."""
        if not self.llm:
            return {
                "language": "English",
                "needs_cgm": False,
                "needs_pump": False,
                "needs_news": False,
                "needs_search": False,
                "search_query": None,
                "fast_answer": None,
                "reply": None,
            }

        start_time = time.time()
        
        # 1. Check cache
        cache_key = hashlib.md5(f"intent:{client_id}:{query}:{language_hint}".encode()).hexdigest()
        cached = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached is not None:
            try:
                return json.loads(cached)
            except:
                pass
        
        try:
            user_prompt = f"User: {query}"
            # Format the system prompt with the language hint for stronger anchoring
            lang_instruction = f"Strictly generate 'search_query' and 'reply' in the language matching the hint: {language_hint}" if language_hint else "Generate 'search_query' and 'reply' in the same language as the user's query."
            
            # Increased timeout to 10s for stronger multilingual stability
            response = self.llm.response_no_stream(
                system_prompt=f"{self.SYSTEM_PROMPT}\n{lang_instruction}",
                user_prompt=user_prompt,
                response_format={"type": "json_object"},
                timeout=10,
                max_retries=0
            )
            
            response_text = response.strip()
            
            # 1. Pre-process: Extract JSON structure if it's wrapped in text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            # JSON Salvage: If we get an unterminated or slightly malformed response
            result = {}
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Attempt to repair simple missing closures
                repaired = response_text
                if not repaired.endswith("}"):
                    if repaired.count('"') % 2 != 0: repaired += '"'
                    repaired += ' }'
                try:
                    result = json.loads(repaired)
                    logger.bind(tag=TAG).debug(f"Salvaged partial JSON response: {repaired}")
                except:
                    # Robust Regex Extraction for key fields
                    logger.bind(tag=TAG).debug(f"JSON parsing failed, using regex extraction on: {response_text}")
                    
                    # Look for needs_search
                    match_search = re.search(r'"needs_search":\s*(true|false)', response_text)
                    if match_search: result["needs_search"] = match_search.group(1) == "true"
                    
                    # Look for fast_answer type
                    match_fast = re.search(r'"fast_answer":\s*"([^"]+)"', response_text)
                    if match_fast: result["fast_answer"] = match_fast.group(1)
                    
                    # Look for search_query strings
                    match_query = re.search(r'"search_query":\s*"([^"]+)"', response_text)
                    if match_query: result["search_query"] = match_query.group(1)

                    # Look for reply strings
                    match_reply = re.search(r'"reply":\s*"([^"]+)"', response_text)
                    if match_reply: result["reply"] = match_reply.group(1)
                    
                    if not result:
                        raise # Rethrow if even regex fails
            
            # Normalize result with safe defaults
            result = {
                "language": str(result.get("language", "English")),
                "needs_cgm": bool(result.get("needs_cgm", False)),
                "needs_pump": bool(result.get("needs_pump", False)),
                "needs_news": bool(result.get("needs_news", False)),
                "needs_search": bool(result.get("needs_search", False)),
                "search_query": result.get("search_query"),
                "fast_answer": result.get("fast_answer"),
                "reply": result.get("reply")
            }
            
            self.cache_manager.set(self.CacheType.INTENT, cache_key, json.dumps(result))
            
            elapsed = time.time() - start_time
            logger.bind(tag=TAG).info(f"Intent classified in {elapsed:.2f}s: {result['fast_answer'] or 'chat'}")
            return result
            
        except Exception as e:
            logger.bind(tag=TAG).warning(f"Intent LLM failed: {e}")
            
            # Rule-based fallback
            query_lower = query.lower()
            needs_pump = any(kw in query_lower for kw in ["pump", "insulin", "bolus", "basal", "泵", "胰岛素"])
            needs_cgm = any(kw in query_lower for kw in ["glucose", "sugar", "cgm", "high", "low", "血糖"])
            
            fast_answer = None
            if needs_pump:
                fast_answer = "pump"
            elif needs_cgm:
                fast_answer = "cgm"
                
            return {
                "language": "English" if "a" <= query_lower[0] <= "z" else "Chinese",
                "needs_cgm": needs_cgm,
                "needs_pump": needs_pump,
                "needs_news": False,
                "needs_search": False,
                "search_query": None,
                "fast_answer": fast_answer,
                "reply": None,
            }
    
    def get_fast_answer(self, answer_type: str, client_id: str = "", battery_level: str = None) -> str:
        """Generate a fast answer for time/weather/location/battery."""
        if answer_type == "time":
            return self._get_time_answer()
        elif answer_type == "weather":
            return self._get_weather_answer(client_id)
        elif answer_type == "location":
            return self._get_location_answer(client_id)
        elif answer_type == "battery":
            if battery_level and battery_level != "unknown":
                return f"The current battery level is {battery_level}%."
            return "I couldn't retrieve the battery level from the device."
        elif answer_type == "volume":
            # For volume, we assume the level is passed or fetched via same lazy sync pattern
            # If battery_level is reused for 'hardware_stat' generically or we pass volume specifically
            # For simplicity, we'll implement _get_volume_answer separately in connection.py 
            # or handle it here if we pass it.
            if battery_level and battery_level != "unknown":
                return f"The current volume level is {battery_level}%."
            return "I couldn't retrieve the volume level from the device."
        elif answer_type == "pump":
            return self._get_pump_answer(client_id)
        elif answer_type == "cgm":
            return self._get_cgm_answer(client_id)
        return None
    
    def _get_time_answer(self) -> str:
        try:
            tz_offset = self.config.get("server", {}).get("timezone_offset", 0)
            if tz_offset == -5: tz = ZoneInfo("America/New_York")
            elif tz_offset == -8: tz = ZoneInfo("America/Los_Angeles")
            else:
                from datetime import timezone, timedelta
                tz = timezone(timedelta(hours=tz_offset))
            
            now = datetime.now(tz)
            time_str = now.strftime("%I:%M %p").lstrip("0")
            day = now.strftime("%A, %B %d")
            return f"It's {time_str} on {day}."
        except:
            return f"It's {datetime.now().strftime('%I:%M %p')}."
    
    def _get_weather_answer(self, client_id: str) -> str:
        try:
            from plugins_func.functions.get_weather import get_weather
            location = self.config.get("plugins", {}).get("get_weather", {}).get("default_location", "")
            if not location: return "I don't have your location set."
            
            import asyncio
            class MockConn:
                def __init__(self, config): self.config = config
            
            mock = MockConn(self.config)
            # get_weather is synchronous in reality
            result = get_weather(mock, location=location)
            if result and hasattr(result, "result"):
                return result.result
            return f"I couldn't get the weather for {location}."
        except:
            return "Weather service is currently unavailable."
    
    def _get_location_answer(self, client_id: str) -> str:
        try:
            config_path = os.path.join("data", client_id, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    location = json.load(f).get("location")
                    if location: return f"We're in {location}."
            return "Location not set in your config."
        except:
            return "Unable to determine your location."

    def _get_pump_answer(self, client_id: str) -> str:
        try:
            from core.utils.pump_manager import PumpManager
            manager = PumpManager(data_root="data")
            status = manager.get_realtime_status(client_id)
            if status:
                return status
            return "I couldn't retrieve recent pump events."
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to get fast pump answer: {e}")
            return "Pump data is temporarily unavailable."

    def _get_cgm_answer(self, client_id: str) -> str:
        try:
            from core.utils.cgm_manager import CGMManager
            manager = CGMManager(data_root="data")
            status = manager.get_realtime_status(client_id)
            if status:
                return status
            return "I couldn't retrieve recent CGM data."
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to get CGM fast answer: {e}")
            return "CGM data is temporarily unavailable."


def get_classifier(config):
    global _classifier
    if _classifier is None:
        _classifier = ContextIntentClassifier(config)
    return _classifier

def classify_context_needs(query: str, client_id: str, config: dict, language_hint: str = None) -> dict:
    classifier = get_classifier(config)
    if not classifier:
        return {
            "language": "English",
            "needs_cgm": False,
            "needs_pump": False,
            "needs_news": False,
            "needs_search": False,
            "search_query": None,
            "fast_answer": None,
            "reply": None,
        }
    return classifier.classify(query, client_id, language_hint=language_hint)

def get_fast_answer(answer_type: str, client_id: str, config: dict, battery_level: str = None) -> str:
    classifier = get_classifier(config)
    return classifier.get_fast_answer(answer_type, client_id, battery_level=battery_level)


def needs_cgm_context(query: str, client_id: str, config: dict) -> bool:
    result = classify_context_needs(query, client_id, config)
    return result.get("needs_cgm", False)


def needs_pump_context(query: str, client_id: str, config: dict) -> bool:
    result = classify_context_needs(query, client_id, config)
    return result.get("needs_pump", False)
