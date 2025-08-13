import asyncio
import logging
import os
import statistics
import time
from typing import Dict
import aiohttp
from tabulate import tabulate
from config.settings import load_config
from core.utils.asr import create_instance as create_stt_instance
from core.utils.llm import create_instance as create_llm_instance
from core.utils.tts import create_instance as create_tts_instance

# Set global log level to WARNING, suppress INFO level logs
logging.basicConfig(level=logging.WARNING)


class AsyncPerformanceTester:
    def __init__(self):
        self.config = load_config()
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "Hello, please introduce yourself",
                "What's the weather like today?",
                "Please summarize the basic principles and application prospects of quantum computing in 100 words",
            ],
        )

        self.test_wav_list = []
        self.wav_root = r"config/assets"
        for file_name in os.listdir(self.wav_root):
            file_path = os.path.join(self.wav_root, file_name)
            # Check if file size is larger than 300KB
            if os.path.getsize(file_path) > 300 * 1024:  # 300KB = 300 * 1024 bytes
                with open(file_path, "rb") as f:
                    self.test_wav_list.append(f.read())

        self.results = {"llm": {}, "tts": {}, "stt": {}, "combinations": []}

    async def _check_ollama_service(self, base_url: str, model_name: str) -> bool:
        """Asynchronously check Ollama service status"""
        async with aiohttp.ClientSession() as session:
            try:
                # Check if service is available
                async with session.get(f"{base_url}/api/version") as response:
                    if response.status != 200:
                        print(
                            f"🚫 Ollama service not started or inaccessible: {base_url}")
                        return False

                # Check if model exists
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        if not any(model["name"] == model_name for model in models):
                            print(
                                f"🚫 Ollama model {model_name} not found, please use ollama pull {model_name} to download first"
                            )
                            return False
                    else:
                        print(f"🚫 Unable to get Ollama model list")
                        return False

                return True
            except Exception as e:
                print(f"🚫 Unable to connect to Ollama service: {str(e)}")
                return False

    async def _test_tts(self, tts_name: str, config: Dict) -> Dict:
        """Asynchronously test single TTS performance"""
        try:
            logging.getLogger("core.providers.tts.base").setLevel(
                logging.WARNING)
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and any(x in config[field] for x in ["你的", "placeholder"])
                for field in token_fields
            ):
                print(
                    f"⏭️ TTS {tts_name} access_token/api_key not configured, skipped")
                return {"name": tts_name, "type": "tts", "errors": 1}

            module_type = config.get("type", tts_name)
            tts = create_tts_instance(
                module_type, config, delete_audio_file=True)

            print(f"🎵 Testing TTS: {tts_name}")
            tmp_file = tts.generate_filename()
            await tts.text_to_speak("Connection test", tmp_file)

            if not tmp_file or not os.path.exists(tmp_file):
                print(f"❌ {tts_name} connection failed")
                return {"name": tts_name, "type": "tts", "errors": 1}

            total_time = 0
            test_count = len(self.test_sentences[:2])

            for i, sentence in enumerate(self.test_sentences[:2], 1):
                start = time.time()
                tmp_file = tts.generate_filename()
                await tts.text_to_speak(sentence, tmp_file)
                duration = time.time() - start
                total_time += duration

                if tmp_file and os.path.exists(tmp_file):
                    print(f"✓ {tts_name} [{i}/{test_count}]")
                else:
                    print(f"✗ {tts_name} [{i}/{test_count}]")
                    return {"name": tts_name, "type": "tts", "errors": 1}

            return {
                "name": tts_name,
                "type": "tts",
                "avg_time": total_time / test_count,
                "errors": 0,
            }

        except Exception as e:
            print(f"⚠️ {tts_name} test failed: {str(e)}")
            return {"name": tts_name, "type": "tts", "errors": 1}

    async def _test_stt(self, stt_name: str, config: Dict) -> Dict:
        """Asynchronously test single STT performance"""
        try:
            logging.getLogger("core.providers.asr.base").setLevel(
                logging.WARNING)
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and any(x in config[field] for x in ["你的", "placeholder"])
                for field in token_fields
            ):
                print(
                    f"⏭️ STT {stt_name} access_token/api_key not configured, skipped")
                return {"name": stt_name, "type": "stt", "errors": 1}

            module_type = config.get("type", stt_name)
            stt = create_stt_instance(
                module_type, config, delete_audio_file=True)
            stt.audio_format = "pcm"

            print(f"🎵 Testing STT: {stt_name}")
            text, _ = await stt.speech_to_text(
                [self.test_wav_list[0]], "1", stt.audio_format
            )

            if text is None:
                print(f"❌ {stt_name} connection failed")
                return {"name": stt_name, "type": "stt", "errors": 1}

            total_time = 0
            test_count = len(self.test_wav_list)

            for i, sentence in enumerate(self.test_wav_list, 1):
                start = time.time()
                text, _ = await stt.speech_to_text([sentence], "1", stt.audio_format)
                duration = time.time() - start
                total_time += duration

                if text:
                    print(f"✓ {stt_name} [{i}/{test_count}]")
                else:
                    print(f"✗ {stt_name} [{i}/{test_count}]")
                    return {"name": stt_name, "type": "stt", "errors": 1}

            return {
                "name": stt_name,
                "type": "stt",
                "avg_time": total_time / test_count,
                "errors": 0,
            }

        except Exception as e:
            print(f"⚠️ {stt_name} test failed: {str(e)}")
            return {"name": stt_name, "type": "stt", "errors": 1}

    async def _test_llm(self, llm_name: str, config: Dict) -> Dict:
        """Asynchronously test single LLM performance"""
        try:
            # For Ollama, skip api_key check and perform special handling
            if llm_name == "Ollama":
                base_url = config.get("base_url", "http://localhost:11434")
                model_name = config.get("model_name")
                if not model_name:
                    print(f"🚫 Ollama model_name not configured")
                    return {"name": llm_name, "type": "llm", "errors": 1}

                if not await self._check_ollama_service(base_url, model_name):
                    return {"name": llm_name, "type": "llm", "errors": 1}
            else:
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"🚫 Skipping unconfigured LLM: {llm_name}")
                    return {"name": llm_name, "type": "llm", "errors": 1}

            # Get actual type (compatible with old configuration)
            module_type = config.get("type", llm_name)
            llm = create_llm_instance(module_type, config)

            # Uniformly use UTF-8 encoding
            test_sentences = [
                s.encode("utf-8").decode("utf-8") for s in self.test_sentences
            ]

            # Create test tasks for all sentences
            sentence_tasks = []
            for sentence in test_sentences:
                sentence_tasks.append(
                    self._test_single_sentence(llm_name, llm, sentence)
                )

            # Execute all sentence tests concurrently
            sentence_results = await asyncio.gather(*sentence_tasks)

            # Process results
            valid_results = [r for r in sentence_results if r is not None]
            if not valid_results:
                print(
                    f"⚠️ {llm_name} no valid data, configuration may be incorrect")
                return {"name": llm_name, "type": "llm", "errors": 1}

            first_token_times = [r["first_token_time"] for r in valid_results]
            response_times = [r["response_time"] for r in valid_results]

            # Filter abnormal data
            mean = statistics.mean(response_times)
            stdev = statistics.stdev(response_times) if len(
                response_times) > 1 else 0
            filtered_times = [
                t for t in response_times if t <= mean + 3 * stdev]

            if len(filtered_times) < len(test_sentences) * 0.5:
                print(
                    f"⚠️ {llm_name} insufficient valid data, network may be unstable")
                return {"name": llm_name, "type": "llm", "errors": 1}

            return {
                "name": llm_name,
                "type": "llm",
                "avg_response": sum(response_times) / len(response_times),
                "avg_first_token": sum(first_token_times) / len(first_token_times),
                "std_first_token": (
                    statistics.stdev(first_token_times)
                    if len(first_token_times) > 1
                    else 0
                ),
                "std_response": (
                    statistics.stdev(response_times) if len(
                        response_times) > 1 else 0
                ),
                "errors": 0,
            }

        except Exception as e:
            print(f"LLM {llm_name} test failed: {str(e)}")
            return {"name": llm_name, "type": "llm", "errors": 1}

    async def _test_single_sentence(self, llm_name: str, llm, sentence: str) -> Dict:
        """Test performance of a single sentence"""
        try:
            print(f"📝 {llm_name} starting test: {sentence[:20]}...")
            sentence_start = time.time()
            first_token_received = False
            first_token_time = None

            async def process_response():
                nonlocal first_token_received, first_token_time
                for chunk in llm.response(
                    "perf_test", [{"role": "user", "content": sentence}]
                ):
                    if not first_token_received and chunk.strip() != "":
                        first_token_time = time.time() - sentence_start
                        first_token_received = True
                        print(
                            f"✓ {llm_name} first token: {first_token_time:.3f}s")
                    yield chunk

            response_chunks = []
            async for chunk in process_response():
                response_chunks.append(chunk)

            response_time = time.time() - sentence_start
            print(f"✓ {llm_name} response completed: {response_time:.3f}s")

            if first_token_time is None:
                first_token_time = (
                    response_time  # If no first token detected, use total response time
                )

            return {
                "name": llm_name,
                "type": "llm",
                "first_token_time": first_token_time,
                "response_time": response_time,
            }

        except Exception as e:
            print(f"⚠️ {llm_name} sentence test failed: {str(e)}")
            return None

    def _generate_combinations(self):
        """Generate best combination recommendations"""
        valid_llms = [
            k
            for k, v in self.results["llm"].items()
            if v["errors"] == 0 and v["avg_first_token"] >= 0.05
        ]
        valid_tts = [k for k, v in self.results["tts"].items()
                     if v["errors"] == 0]
        valid_stt = [k for k, v in self.results["stt"].items()
                     if v["errors"] == 0]

        # Find benchmark values
        min_first_token = (
            min([self.results["llm"][llm]["avg_first_token"]
                for llm in valid_llms])
            if valid_llms
            else 1
        )
        min_tts_time = (
            min([self.results["tts"][tts]["avg_time"] for tts in valid_tts])
            if valid_tts
            else 1
        )
        min_stt_time = (
            min([self.results["stt"][stt]["avg_time"] for stt in valid_stt])
            if valid_stt
            else 1
        )

        for llm in valid_llms:
            for tts in valid_tts:
                for stt in valid_stt:
                    # Calculate relative performance score (smaller is better)
                    llm_score = (
                        self.results["llm"][llm]["avg_first_token"] /
                        min_first_token
                    )
                    tts_score = self.results["tts"][tts]["avg_time"] / \
                        min_tts_time
                    stt_score = self.results["stt"][stt]["avg_time"] / \
                        min_stt_time

                    # Calculate stability score (standard deviation/average, smaller is more stable)
                    llm_stability = (
                        self.results["llm"][llm]["std_first_token"]
                        / self.results["llm"][llm]["avg_first_token"]
                    )

                    # Comprehensive score (considering performance and stability)
                    # LLM score: performance weight(70%) + stability weight(30%)
                    llm_final_score = llm_score * 0.7 + llm_stability * 0.3

                    # Total score = LLM score(70%) + TTS score(30%) + STT score(30%)
                    total_score = (
                        llm_final_score * 0.7 + tts_score * 0.3 + stt_score * 0.3
                    )

                    self.results["combinations"].append(
                        {
                            "llm": llm,
                            "tts": tts,
                            "stt": stt,
                            "score": total_score,
                            "details": {
                                "llm_first_token": self.results["llm"][llm][
                                    "avg_first_token"
                                ],
                                "llm_stability": llm_stability,
                                "tts_time": self.results["tts"][tts]["avg_time"],
                                "stt_time": self.results["stt"][stt]["avg_time"],
                            },
                        }
                    )

        # Smaller score is better
        self.results["combinations"].sort(key=lambda x: x["score"])

    def _print_results(self):
        """Print test results"""
        llm_table = []
        for name, data in self.results["llm"].items():
            if data["errors"] == 0:
                stability = data["std_first_token"] / data["avg_first_token"]
                llm_table.append(
                    [
                        name,  # No need for fixed width, let tabulate handle alignment
                        f"{data['avg_first_token']:.3f}s",
                        f"{data['avg_response']:.3f}s",
                        f"{stability:.3f}",
                    ]
                )

        if llm_table:
            print("\nLLM Performance Rankings:\n")
            print(
                tabulate(
                    llm_table,
                    headers=["Model Name", "First Token Time",
                             "Total Time", "Stability"],
                    tablefmt="github",
                    colalign=("left", "right", "right", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ No available LLM modules for testing.")

        tts_table = []
        for name, data in self.results["tts"].items():
            if data["errors"] == 0:
                # No need for fixed width
                tts_table.append([name, f"{data['avg_time']:.3f}s"])

        if tts_table:
            print("\nTTS Performance Rankings:\n")
            print(
                tabulate(
                    tts_table,
                    headers=["Model Name", "Synthesis Time"],
                    tablefmt="github",
                    colalign=("left", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ No available TTS modules for testing.")

        stt_table = []
        for name, data in self.results["stt"].items():
            if data["errors"] == 0:
                # No need for fixed width
                stt_table.append([name, f"{data['avg_time']:.3f}s"])

        if stt_table:
            print("\nSTT Performance Rankings:\n")
            print(
                tabulate(
                    stt_table,
                    headers=["Model Name", "Recognition Time"],
                    tablefmt="github",
                    colalign=("left", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ No available STT modules for testing.")

        if self.results["combinations"]:
            print("\nRecommended Configuration Combinations (smaller score is better):\n")
            combo_table = []
            for combo in self.results["combinations"][:5]:
                combo_table.append(
                    [
                        # No need for fixed width
                        f"{combo['llm']} + {combo['tts']} + {combo['stt']}",
                        f"{combo['score']:.3f}",
                        f"{combo['details']['llm_first_token']:.3f}s",
                        f"{combo['details']['llm_stability']:.3f}",
                        f"{combo['details']['tts_time']:.3f}s",
                        f"{combo['details']['stt_time']:.3f}s",
                    ]
                )

            print(
                tabulate(
                    combo_table,
                    headers=[
                        "Combination Plan",
                        "Comprehensive Score",
                        "LLM First Token Time",
                        "Stability",
                        "TTS Synthesis Time",
                        "STT Recognition Time",
                    ],
                    tablefmt="github",
                    colalign=("left", "right", "right",
                              "right", "right", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ No available module combination recommendations.")

    def _process_results(self, all_results):
        """Process test results"""
        for result in all_results:
            if result["errors"] == 0:
                if result["type"] == "llm":
                    self.results["llm"][result["name"]] = result
                elif result["type"] == "tts":
                    self.results["tts"][result["name"]] = result
                elif result["type"] == "stt":
                    self.results["stt"][result["name"]] = result
                else:
                    pass

    async def run(self):
        """Execute full asynchronous testing"""
        print("🔍 Starting to filter available modules...")

        # Create all test tasks
        all_tasks = []

        # LLM test tasks
        if self.config.get("LLM") is not None:
            for llm_name, config in self.config.get("LLM", {}).items():
                # Check configuration validity
                if llm_name == "CozeLLM":
                    if any(x in config.get("bot_id", "") for x in ["你的"]) or any(
                        x in config.get("user_id", "") for x in ["你的"]
                    ):
                        print(
                            f"⏭️ LLM {llm_name} bot_id/user_id not configured, skipped")
                        continue
                elif "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"⏭️ LLM {llm_name} api_key not configured, skipped")
                    continue

                # For Ollama, check service status first
                if llm_name == "Ollama":
                    base_url = config.get("base_url", "http://localhost:11434")
                    model_name = config.get("model_name")
                    if not model_name:
                        print(f"🚫 Ollama model_name not configured")
                        continue

                    if not await self._check_ollama_service(base_url, model_name):
                        continue

                print(f"📋 Adding LLM test task: {llm_name}")
                module_type = config.get("type", llm_name)
                llm = create_llm_instance(module_type, config)

                # Create independent tasks for each sentence
                for sentence in self.test_sentences:
                    sentence = sentence.encode("utf-8").decode("utf-8")
                    all_tasks.append(
                        self._test_single_sentence(llm_name, llm, sentence)
                    )

        # TTS test tasks
        if self.config.get("TTS") is not None:
            for tts_name, config in self.config.get("TTS", {}).items():
                token_fields = ["access_token", "api_key", "token"]
                if any(
                    field in config
                    and any(x in config[field] for x in ["你的", "placeholder"])
                    for field in token_fields
                ):
                    print(
                        f"⏭️ TTS {tts_name} access_token/api_key not configured, skipped")
                    continue

                print(f"🎵 Adding TTS test task: {tts_name}")
                all_tasks.append(self._test_tts(tts_name, config))

        # STT test tasks
        if len(self.test_wav_list) >= 1:
            if self.config.get("ASR") is not None:
                for stt_name, config in self.config.get("ASR", {}).items():
                    token_fields = ["access_token", "api_key", "token"]
                    if any(
                        field in config
                        and any(x in config[field] for x in ["你的", "placeholder"])
                        for field in token_fields
                    ):
                        print(
                            f"⏭️ ASR {stt_name} access_token/api_key not configured, skipped")
                        continue

                    print(f"🎵 Adding ASR test task: {stt_name}")
                    all_tasks.append(self._test_stt(stt_name, config))
        else:
            print(
                f"\n⚠️ No audio files found in {self.wav_root} path, STT test tasks skipped")

        print(
            f"\n✅ Found {len([t for t in all_tasks if 'test_single_sentence' in str(t)]) / len(self.test_sentences):.0f} available LLM modules"
        )
        print(
            f"✅ Found {len([t for t in all_tasks if '_test_tts' in str(t)])} available TTS modules"
        )
        print(
            f"✅ Found {len([t for t in all_tasks if '_test_stt' in str(t)])} available STT modules"
        )

        print("\n⏳ Starting concurrent testing of all modules...\n")

        # Execute all test tasks concurrently
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Process LLM results
        llm_results = {}
        for result in [
            r
            for r in all_results
            if r and isinstance(r, dict) and r.get("type") == "llm"
        ]:
            llm_name = result["name"]
            if llm_name not in llm_results:
                llm_results[llm_name] = {
                    "name": llm_name,
                    "type": "llm",
                    "first_token_times": [],
                    "response_times": [],
                    "errors": 0,
                }

            llm_results[llm_name]["first_token_times"].append(
                result["first_token_time"]
            )
            llm_results[llm_name]["response_times"].append(
                result["response_time"])

        # Calculate LLM averages and standard deviations
        for llm_name, data in llm_results.items():
            if len(data["first_token_times"]) >= len(self.test_sentences) * 0.5:
                self.results["llm"][llm_name] = {
                    "name": llm_name,
                    "type": "llm",
                    "avg_response": sum(data["response_times"])
                    / len(data["response_times"]),
                    "avg_first_token": sum(data["first_token_times"])
                    / len(data["first_token_times"]),
                    "std_first_token": (
                        statistics.stdev(data["first_token_times"])
                        if len(data["first_token_times"]) > 1
                        else 0
                    ),
                    "std_response": (
                        statistics.stdev(data["response_times"])
                        if len(data["response_times"]) > 1
                        else 0
                    ),
                    "errors": 0,
                }

        # Process TTS results
        for result in [
            r
            for r in all_results
            if r and isinstance(r, dict) and r.get("type") == "tts"
        ]:
            if result["errors"] == 0:
                self.results["tts"][result["name"]] = result

        # Process STT results
        for result in [
            r
            for r in all_results
            if r and isinstance(r, dict) and r.get("type") == "stt"
        ]:
            if result["errors"] == 0:
                self.results["stt"][result["name"]] = result

        # Generate combination recommendations and print results
        print("\n📊 Generating test report...")
        self._generate_combinations()
        self._print_results()


async def main():
    tester = AsyncPerformanceTester()
    await tester.run()

if __name__ == "__main__":
    asyncio.run(main())
