import asyncio
import logging
import os
import statistics
import time
import concurrent.futures
from typing import Dict, Optional
import yaml
import aiohttp
from tabulate import tabulate
from core.utils.llm import create_instance as create_llm_instance
from config.settings import load_config

# Set global log level to WARNING to suppress INFO level logs
logging.basicConfig(level=logging.WARNING)

description = "Large Language Model performance test"


class LLMPerformanceTester:
    def __init__(self):
        self.config = load_config()
        # Use test content more suitable for agent scenarios, including system prompts
        self.system_prompt = self._load_system_prompt()
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "Hello, I'm feeling down today, can you comfort me?",
                "Can you help me check tomorrow's weather?",
                "I'd like to hear an interesting story, can you tell me one?",
                "What time is it now? What day of the week is it?",
                "I want to set an alarm for 8 AM tomorrow to remind me of a meeting",
            ],
        )
        self.results = {}

    def _load_system_prompt(self) -> str:
        """Load system prompt"""
        try:
            prompt_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), self.config.get("prompt_template", "agent-base-prompt.txt")
            )
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Replace template variables with test values
                content = content.replace(
                    "{{base_prompt}}", "You are Xiaozhi, a smart and cute AI assistant"
                )
                content = content.replace(
                    "{{emojiList}}", "😀,😃,😄,😁,😊,😍,🤔,😮,😱,😢,😭,😴,😵,🤗,🙄"
                )
                content = content.replace("{{current_time}}", "August 17, 2024 12:30:45")
                content = content.replace("{{today_date}}", "August 17, 2024")
                content = content.replace("{{today_weekday}}", "Saturday")
                content = content.replace("{{formatted_date}}", "August 17, 2024")
                content = content.replace("{{local_address}}", "San Francisco")
                content = content.replace("{{weather_info}}", "Today sunny, 25-32°C")
                return content
        except Exception as e:
            print(f"Unable to load system prompt file: {e}")
            return "You are Xiaozhi, a smart and cute AI assistant. Please reply to users with a warm and friendly tone."

    def _collect_response_sync(self, llm, messages, llm_name, sentence_start):
        """Helper method for synchronous response data collection"""
        chunks = []
        first_token_received = False
        first_token_time = None

        try:
            response_generator = llm.response("perf_test", messages)
            chunk_count = 0
            for chunk in response_generator:
                chunk_count += 1
                # Check if should interrupt after processing certain number of chunks
                if chunk_count % 10 == 0:
                    # Exit early by checking if current thread is marked for interruption
                    import threading

                    if (
                        threading.current_thread().ident
                        != threading.main_thread().ident
                    ):
                        # If not main thread, check if should stop
                        pass

                # Check if chunk contains error information
                chunk_str = str(chunk)
                if (
                    "exception" in chunk_str.lower()
                    or "error" in chunk_str.lower()
                    or "502" in chunk_str.lower()
                ):
                    error_msg = chunk_str.lower()
                    print(f"{llm_name} response contains error information: {error_msg}")
                    # Throw an exception containing error information
                    raise Exception(chunk_str)

                if not first_token_received and chunk.strip() != "":
                    first_token_time = time.time() - sentence_start
                    first_token_received = True
                    print(f"{llm_name} first Token: {first_token_time:.3f}s")
                chunks.append(chunk)
        except Exception as e:
            # More detailed error information
            error_msg = str(e).lower()
            print(f"{llm_name} response collection exception: {error_msg}")
            # For 502 errors or network errors, directly throw exception for upper layer handling
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
                or "exception" in str(e)
                or "error" in str(e)
            ):
                raise e
            # For other errors, can return partial results
            return chunks, first_token_time

        return chunks, first_token_time

    async def _check_ollama_service(self, base_url: str, model_name: str) -> bool:
        """Asynchronously check Ollama service status"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/api/version") as response:
                    if response.status != 200:
                        print(f"Ollama service not started or inaccessible: {base_url}")
                        return False
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        if not any(model["name"] == model_name for model in models):
                            print(
                                f"Ollama model {model_name} not found, please use `ollama pull {model_name}` to download first"
                            )
                            return False
                    else:
                        print("Unable to get Ollama model list")
                        return False
                return True
            except Exception as e:
                print(f"Unable to connect to Ollama service: {str(e)}")
                return False

    async def _test_single_sentence(
        self, llm_name: str, llm, sentence: str
    ) -> Optional[Dict]:
        """Test performance of a single sentence"""
        try:
            print(f"{llm_name} starting test: {sentence[:20]}...")
            sentence_start = time.time()
            first_token_received = False
            first_token_time = None

            # Build messages containing system prompts
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": sentence},
            ]

            # Use asyncio.wait_for for timeout control
            try:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Create response collection task
                    future = executor.submit(
                        self._collect_response_sync,
                        llm,
                        messages,
                        llm_name,
                        sentence_start,
                    )

                    # Use asyncio.wait_for to implement timeout control
                    try:
                        response_chunks, first_token_time = await asyncio.wait_for(
                            asyncio.wrap_future(future), timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        print(f"{llm_name} test timeout (10 seconds), skipping")
                        # Force cancel future
                        future.cancel()
                        # Wait a short time to ensure thread pool task can respond to cancellation
                        try:
                            await asyncio.wait_for(
                                asyncio.wrap_future(future), timeout=1.0
                            )
                        except (
                            asyncio.TimeoutError,
                            concurrent.futures.CancelledError,
                            Exception,
                        ):
                            # Ignore all exceptions to ensure program continues
                            pass
                        return None

            except Exception as timeout_error:
                print(f"{llm_name} handling exception: {timeout_error}")
                return None

            response_time = time.time() - sentence_start
            print(f"{llm_name} response completed: {response_time:.3f}s")

            return {
                "name": llm_name,
                "type": "llm",
                "first_token_time": first_token_time,
                "response_time": response_time,
            }
        except Exception as e:
            error_msg = str(e).lower()
            # Check if it's a 502 error or network error
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
            ):
                print(f"{llm_name} encountered 502 error, skipping test")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "502 network error",
                }
            print(f"{llm_name} sentence test failed: {str(e)}")
            return None

    async def _test_llm(self, llm_name: str, config: Dict) -> Dict:
        """Asynchronously test single LLM performance"""
        try:
            # For Ollama, skip api_key check and perform special handling
            if llm_name == "Ollama":
                base_url = config.get("base_url", "http://localhost:11434")
                model_name = config.get("model_name")
                if not model_name:
                    print("Ollama model_name not configured")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "network error",
                    }

                if not await self._check_ollama_service(base_url, model_name):
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "network error",
                    }
            else:
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["your", "placeholder", "sk-xxx"]
                ):
                    print(f"Skipping unconfigured LLM: {llm_name}")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "configuration error",
                    }

            # Get actual type (compatible with old configuration)
            module_type = config.get("type", llm_name)
            llm = create_llm_instance(module_type, config)

            # Use UTF-8 encoding uniformly
            test_sentences = [
                s.encode("utf-8").decode("utf-8") for s in self.test_sentences
            ]

            # Create test tasks for all sentences
            sentence_tasks = []
            for sentence in test_sentences:
                sentence_tasks.append(
                    self._test_single_sentence(llm_name, llm, sentence)
                )

            # Execute all sentence tests concurrently and handle possible exceptions
            sentence_results = await asyncio.gather(
                *sentence_tasks, return_exceptions=True
            )

            # Process results, filter out exceptions and None values
            valid_results = []
            for result in sentence_results:
                if isinstance(result, dict) and result is not None:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    error_msg = str(result).lower()
                    if "502" in error_msg or "bad gateway" in error_msg:
                        print(f"{llm_name} encountered 502 error, skipping this sentence test")
                        return {
                            "name": llm_name,
                            "type": "llm",
                            "errors": 1,
                            "error_type": "502 network error",
                        }
                    else:
                        print(f"{llm_name} sentence test exception: {result}")

            if not valid_results:
                print(f"{llm_name} no valid data, possible network issues or configuration errors")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "Network error",
                }

            # Check valid result count, if too few consider test failed
            if len(valid_results) < len(test_sentences) * 0.3:  # At least 30% success rate
                print(
                    f"{llm_name} too few successful test sentences ({len(valid_results)}/{len(test_sentences)}), possible network instability or interface issues"
                )
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "Network error",
                }

            first_token_times = [
                r["first_token_time"]
                for r in valid_results
                if r.get("first_token_time")
            ]
            response_times = [r["response_time"] for r in valid_results]

            # Filter abnormal data (data beyond 3 standard deviations)
            if len(response_times) > 1:
                mean = statistics.mean(response_times)
                stdev = statistics.stdev(response_times)
                filtered_times = [t for t in response_times if t <= mean + 3 * stdev]
            else:
                filtered_times = response_times

            return {
                "name": llm_name,
                "type": "llm",
                "avg_response": sum(response_times) / len(response_times),
                "avg_first_token": (
                    sum(first_token_times) / len(first_token_times)
                    if first_token_times
                    else 0
                ),
                "success_rate": f"{len(valid_results)}/{len(test_sentences)}",
                "errors": 0,
            }
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                print(f"LLM {llm_name} encountered 502 error, skipping test")
            else:
                print(f"LLM {llm_name} test failed: {str(e)}")
            error_type = "network error"
            if "timeout" in str(e).lower():
                error_type = "timeout connection"
            return {
                "name": llm_name,
                "type": "llm",
                "errors": 1,
                "error_type": error_type,
            }

    def _print_results(self):
        """Print test results"""
        print("\n" + "=" * 50)
        print("LLM Performance Test Results")
        print("=" * 50)

        if not self.results:
            print("No available test results")
            return

        headers = ["Model Name", "Average Response Time(s)", "First Token Time(s)", "Success Rate", "Status"]
        table_data = []

        # Collect all data and categorize
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # Normal results
                avg_response = f"{data['avg_response']:.3f}"
                avg_first_token = (
                    f"{data['avg_first_token']:.3f}"
                    if data["avg_first_token"] > 0
                    else "-"
                )
                success_rate = data.get("success_rate", "N/A")
                status = "✅ Normal"

                # Save values for sorting
                first_token_value = (
                    data["avg_first_token"]
                    if data["avg_first_token"] > 0
                    else float("inf")
                )

                valid_results.append(
                    {
                        "name": name,
                        "avg_response": avg_response,
                        "avg_first_token": avg_first_token,
                        "success_rate": success_rate,
                        "status": status,
                        "sort_key": first_token_value,
                    }
                )
            else:
                # Error results
                avg_response = "-"
                avg_first_token = "-"
                success_rate = "0/5"

                # Get specific error type
                error_type = data.get("error_type", "network error")
                status = f"❌ {error_type}"

                error_results.append(
                    [name, avg_response, avg_first_token, success_rate, status]
                )

        # Sort by first token time in ascending order
        valid_results.sort(key=lambda x: x["sort_key"])

        # Convert sorted valid results to table data
        for result in valid_results:
            table_data.append(
                [
                    result["name"],
                    result["avg_response"],
                    result["avg_first_token"],
                    result["success_rate"],
                    result["status"],
                ]
            )

        # Add error results to end of table data
        table_data.extend(error_results)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("\nTest Description:")
        print("- Test content: Agent dialogue scenarios with complete system prompts")
        print("- Timeout control: Maximum wait time for single request is 10 seconds")
        print("- Error handling: Automatically skip models with 502 errors and network exceptions")
        print("- Success rate: Number of successful responses / Total test sentences")
        print("\nTest completed!")

    async def run(self):
        """Execute full asynchronous testing"""
        print("Starting to filter available LLM modules...")

        # Create all test tasks
        all_tasks = []

        # LLM test tasks
        if self.config.get("LLM") is not None:
            for llm_name, config in self.config.get("LLM", {}).items():
                # Check configuration validity
                if llm_name == "OpenAILLM":
                    if any(x in config.get("bot_id", "") for x in ["your"]) or any(
                        x in config.get("user_id", "") for x in ["your"]
                    ):
                        print(f"LLM {llm_name} bot_id/user_id not configured, skipped")
                        continue
                elif "api_key" in config and any(
                    x in config["api_key"] for x in ["your", "placeholder", "sk-xxx"]
                ):
                    print(f"LLM {llm_name} api_key not configured, skipped")
                    continue

                # For Ollama, check service status first
                if llm_name == "Ollama":
                    base_url = config.get("base_url", "http://localhost:11434")
                    model_name = config.get("model_name")
                    if not model_name:
                        print("Ollama model_name not configured")
                        continue

                    if not await self._check_ollama_service(base_url, model_name):
                        continue

                print(f"Adding LLM test task: {llm_name}")
                all_tasks.append(self._test_llm(llm_name, config))

        print(f"\nFound {len(all_tasks)} available LLM modules")
        print("\nStarting concurrent testing of all modules...\n")

        # Execute all test tasks concurrently, but set independent timeout for each task
        async def test_with_timeout(task, timeout=30):
            """Add timeout protection for each test task"""
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"Test task timeout ({timeout} seconds), skipping")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "timeout connection",
                }
            except Exception as e:
                print(f"Test task exception: {str(e)}")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "Network error",
                }

        # Wrap timeout protection for each task
        protected_tasks = [test_with_timeout(task) for task in all_tasks]

        # Execute all test tasks concurrently
        all_results = await asyncio.gather(*protected_tasks, return_exceptions=True)

        # Process results
        for result in all_results:
            if isinstance(result, dict):
                if result.get("errors") == 0:
                    self.results[result["name"]] = result
                else:
                    # Record even with errors, for displaying failure status
                    if result.get("name") != "Unknown":
                        self.results[result["name"]] = result
            elif isinstance(result, Exception):
                print(f"Test result processing exception: {str(result)}")

        # Print results
        print("\nGenerating test report...")
        self._print_results()


async def main():
    config = await load_config()
    tester = LLMPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
