import asyncio
import logging
import os
import time
import threading
from typing import Dict
import yaml
from tabulate import tabulate

# 确保从 core.utils.tts 导入 create_tts_instance
from core.utils.tts import create_instance as create_tts_instance
from config.settings import load_config

# 设置全局日志级别为 WARNING
logging.basicConfig(level=logging.WARNING)

description = "非流式语音合成性能测试"


class TTSPerformanceTester:
    def __init__(self, config):
        self.config = config
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "永和九年，岁在癸丑，暮春之初；",
                "夫人之相与，俯仰一世，或取诸怀抱，悟言一室之内；或因寄所托，放浪形骸之外。虽趣舍万殊，静躁不同，",
                "每览昔人兴感之由，若合一契，未尝不临文嗟悼，不能喻之于怀。固知一死生为虚诞，齐彭殇为妄作。",
            ],
        )
        self.results = {}

    async def _test_tts(self, tts_name: str, config: Dict) -> Dict:
        """测试单个TTS模块的性能"""
        try:
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and any(x in config[field] for x in ["你的", "placeholder"])
                for field in token_fields
            ):
                print(f"TTS {tts_name} 未配置access_token/api_key，已跳过")
                return {"name": tts_name, "errors": 1}

            module_type = config.get("type", tts_name)
            tts = create_tts_instance(module_type, config, delete_audio_file=True)

            # 设置 mock conn 对象，避免 TTS 实现访问 self.conn.sample_rate 时为 None
            class MockConn:
                sample_rate = 16000
                audio_format = "pcm"
                stop_event = threading.Event()  # 需要是真正的 Event 对象
                client_abort = False
                headers = {}
            tts.conn = MockConn()

            # 设置 mock opus_encoder，避免某些 TTS 访问 self.opus_encoder 时为 None
            class MockOpusEncoder:
                pass
            if not hasattr(tts, 'opus_encoder') or tts.opus_encoder is None:
                tts.opus_encoder = MockOpusEncoder()

            print(f"测试 TTS: {tts_name}")

            # 连接测试
            tmp_file = tts.generate_filename()
            await tts.text_to_speak("连接测试", tmp_file)

            if not tmp_file or not os.path.exists(tmp_file):
                print(f"{tts_name} 连接失败")
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
                    print(f"{tts_name} [{i}/{test_count}] 测试成功")
                else:
                    print(f"{tts_name} [{i}/{test_count}] 测试失败")
                    return {"name": tts_name, "errors": 1}

            return {
                "name": tts_name,
                "avg_time": total_time / test_count,
                "errors": 0,
            }

        except Exception as e:
            print(f"{tts_name} 测试失败: {str(e)}")
            return {"name": tts_name, "errors": 1}

    def _print_results(self):
        """打印测试结果"""
        if not self.results:
            print("没有有效的TTS测试结果")
            return

        headers = ["TTS模块", "平均耗时(秒)", "测试句子数", "状态"]
        table_data = []

        # 收集所有数据并分类
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # 正常结果
                avg_time = f"{data['avg_time']:.3f}"
                test_count = len(self.test_sentences[:3])
                status = "✅ 正常"
                
                # 保存用于排序的值
                valid_results.append({
                    "name": name,
                    "avg_time": avg_time,
                    "test_count": test_count,
                    "status": status,
                    "sort_key": data['avg_time']
                })
            else:
                # 错误结果
                avg_time = "-"
                test_count = "0/3"
                
                # 默认错误类型为网络错误
                error_type = "网络错误"
                status = f"❌ {error_type}"
                
                error_results.append([name, avg_time, test_count, status])

        # 按平均耗时升序排序
        valid_results.sort(key=lambda x: x["sort_key"])

        # 将排序后的有效结果转换为表格数据
        for result in valid_results:
            table_data.append([
                result["name"],
                result["avg_time"],
                result["test_count"],
                result["status"]
            ])

        # 将错误结果添加到表格数据末尾
        table_data.extend(error_results)

        print("\nTTS性能测试结果:")
        print(
            tabulate(
                table_data,
                headers=headers,
                tablefmt="grid",
                colalign=("left", "right", "right", "left"),
            )
        )
        print("\n测试说明:")
        print("- 超时控制: 单个请求最大等待时间为10秒")
        print("- 错误处理: 无法连接和超时的列为网络错误")
        print("- 排序规则: 按平均耗时从快到慢排序")

    async def run(self):
        """执行测试"""
        print("开始TTS性能测试...")

        if not self.config.get("TTS"):
            print("配置文件中未找到TTS配置")
            return

        # 遍历所有TTS配置
        tasks = []
        for tts_name, config in self.config.get("TTS", {}).items():
            tasks.append(self._test_tts(tts_name, config))

        # 并发执行测试
        results = await asyncio.gather(*tasks)

        # 保存所有结果，包括错误
        for result in results:
            self.results[result["name"]] = result

        # 打印结果
        self._print_results()


# 为了performance_tester.py的调用需求
async def main():
    config = await load_config()
    tester = TTSPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
