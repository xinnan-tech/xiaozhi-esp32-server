import asyncio
import logging
import os
import time
from typing import Dict
import yaml
from tabulate import tabulate

# Ensure import create_tts_instance from core.utils.tts
from core.utils.tts import create_instance as create_tts_instance
from config.settings import load_config

# Set global log level to WARNING
logging.basicConfig(level=logging.WARNING)

description = "Non-streaming speech synthesis performance test"


class TTSPerformanceTester:
    def __init__(self, config):
        self.config = config
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "In the ninth year of Yonghe, the year was Guichou, at the beginning of late spring;",
                "When people interact with each other, they spend their lives together, some sharing their thoughts in intimate conversations within a room; others finding solace in external pursuits, letting their spirits roam freely. Although their interests differ greatly, their quiet and active natures are different,",
                "Every time I read about the reasons why people of the past were moved, it seems like a perfect match, and I cannot help but sigh with emotion when reading, unable to express it in words. I know that treating life and death as equal is absurd, and equating Peng and Shang is delusional.",
            ],
        )
        self.results = {}

    async def _test_tts(self, tts_name: str, config: Dict) -> Dict:
        """Test performance of a single TTS module"""
        try:
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and any(x in config[field] for x in ["your", "placeholder"])
                for field in token_fields
            ):
                print(f"TTS {tts_name} not configured with access_token/api_key, skipped")
                return {"name": tts_name, "errors": 1}

            module_type = config.get("type", tts_name)
            tts = create_tts_instance(module_type, config, delete_audio_file=True)

            print(f"Testing TTS: {tts_name}")

            # Connection test
            tmp_file = tts.generate_filename()
            await tts.text_to_speak("Connection test", tmp_file)

            if not tmp_file or not os.path.exists(tmp_file):
                print(f"{tts_name} connection failed")
                return {"name": tts_name, "errors": 1}

            total_time = 0
            test_count = len(self.test_sentences[:3])

            for i, sentence in enumerate(self.test_sentences[:2], 1):
                start = time.time()
                tmp_file = tts.generate_filename()
                await tts.text_to_speak(sentence, tmp_file)
                duration = time.time() - start
                total_time += duration

                if tmp_file and os.path.exists(tmp_file):
                    print(f"{tts_name} [{i}/{test_count}] test successful")
                else:
                    print(f"{tts_name} [{i}/{test_count}] test failed")
                    return {"name": tts_name, "errors": 1}

            return {
                "name": tts_name,
                "avg_time": total_time / test_count,
                "errors": 0,
            }

        except Exception as e:
            print(f"{tts_name} test failed: {str(e)}")
            return {"name": tts_name, "errors": 1}

    def _print_results(self):
        """Print test results"""
        if not self.results:
            print("No valid TTS test results")
            return

        headers = ["TTS Module", "Average Time (seconds)", "Test Sentences", "Status"]
        table_data = []

        # Collect and categorize all data
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # Normal results
                avg_time = f"{data['avg_time']:.3f}"
                test_count = len(self.test_sentences[:3])
                status = "✅ Normal"
                
                # Save values for sorting
                valid_results.append({
                    "name": name,
                    "avg_time": avg_time,
                    "test_count": test_count,
                    "status": status,
                    "sort_key": data['avg_time']
                })
            else:
                # Error results
                avg_time = "-"
                test_count = "0/3"
                
                # Default error type is network error
                error_type = "Network error"
                status = f"❌ {error_type}"
                
                error_results.append([name, avg_time, test_count, status])

        # Sort by average time in ascending order
        valid_results.sort(key=lambda x: x["sort_key"])

        # Convert sorted valid results to table data
        for result in valid_results:
            table_data.append([
                result["name"],
                result["avg_time"],
                result["test_count"],
                result["status"]
            ])

        # Add error results to end of table data
        table_data.extend(error_results)

        print("\nTTS Performance Test Results:")
        print(
            tabulate(
                table_data,
                headers=headers,
                tablefmt="grid",
                colalign=("left", "right", "right", "left"),
            )
        )
        print("\nTest Instructions:")
        print("- Timeout control: Maximum wait time for single request is 10 seconds")
        print("- Error handling: Connection failures and timeouts are marked as network errors")
        print("- Sorting rule: Sort by average time from fast to slow")

    async def run(self):
        """Execute test"""
        print("Starting TTS performance test...")

        if not self.config.get("TTS"):
            print("TTS configuration not found in config file")
            return

        # Iterate through all TTS configurations
        tasks = []
        for tts_name, config in self.config.get("TTS", {}).items():
            tasks.append(self._test_tts(tts_name, config))

        # Execute tests concurrently
        results = await asyncio.gather(*tasks)

        # Save all results, including errors
        for result in results:
            self.results[result["name"]] = result

        # Print results
        self._print_results()


# For performance_tester.py calling requirements
async def main():
    config = await load_config()
    tester = TTSPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
