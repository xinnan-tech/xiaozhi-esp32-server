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

# 设置全局日志级别为 WARNING，抑制 INFO 级别日志
logging.basicConfig(level=logging.WARNING)

description = "大语言模型性能测试"


class LLMPerformanceTester:
    def __init__(self, config):
        self.config = config
        # 使用更符合智能体场景的测试内容，包含系统提示词
        self.system_prompt = self._load_system_prompt()
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "你好，我今天心情不太好，能安慰一下我吗？",
                "帮我查一下明天的天气如何？",
                "我想听一个有趣的故事，你能给我讲一个吗？",
                "现在几点了？今天是星期几？",
                "我想设置一个明天早上8点的闹钟提醒我开会",
            ],
        )
        self.results = {}

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        try:
            prompt_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), self.config.get("prompt_template", "agent-base-prompt.txt")
            )
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
                # 替换模板变量为测试值
                content = content.replace(
                    "{{base_prompt}}", "你是小智，一个聪明可爱的AI助手"
                )
                content = content.replace(
                    "{{emojiList}}", "😀,😃,😄,😁,😊,😍,🤔,😮,😱,😢,😭,😴,😵,🤗,🙄"
                )
                content = content.replace("{{current_time}}", "2024年8月17日 12:30:45")
                content = content.replace("{{today_date}}", "2024年8月17日")
                content = content.replace("{{today_weekday}}", "星期六")
                content = content.replace("{{lunar_date}}", "甲辰年七月十四")
                content = content.replace("{{local_address}}", "北京市")
                content = content.replace("{{weather_info}}", "今天晴，25-32℃")
                return content
        except Exception as e:
            print(f"无法加载系统提示词文件: {e}")
            return "你是小智，一个聪明可爱的AI助手。请用温暖友善的语气回复用户。"

    def _collect_response_sync(self, llm, messages, llm_name, sentence_start):
        """同步收集响应数据的辅助方法"""
        chunks = []
        first_token_received = False
        first_token_time = None

        try:
            response_generator = llm.response("perf_test", messages)
            chunk_count = 0
            for chunk in response_generator:
                chunk_count += 1
                # 每处理一定数量的chunk就检查一下是否应该中断
                if chunk_count % 10 == 0:
                    # 通过检查当前线程是否被标记为中断来提前退出
                    import threading

                    if (
                        threading.current_thread().ident
                        != threading.main_thread().ident
                    ):
                        # 如果不是主线程，检查是否应该停止
                        pass

                # 检查chunk是否包含错误信息
                chunk_str = str(chunk)
                if (
                    "异常" in chunk_str
                    or "错误" in chunk_str
                    or "502" in chunk_str.lower()
                ):
                    error_msg = chunk_str.lower()
                    print(f"{llm_name} 响应包含错误信息: {error_msg}")
                    # 抛出一个包含错误信息的异常
                    raise Exception(chunk_str)

                if not first_token_received and chunk.strip() != "":
                    first_token_time = time.time() - sentence_start
                    first_token_received = True
                    print(f"{llm_name} 首个 Token: {first_token_time:.3f}s")
                chunks.append(chunk)
        except Exception as e:
            # 更详细的错误信息
            error_msg = str(e).lower()
            print(f"{llm_name} 响应收集异常: {error_msg}")
            # 对于502错误或网络错误，直接抛出异常让上层处理
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
                or "异常" in str(e)
                or "错误" in str(e)
            ):
                raise e
            # 对于其他错误，可以返回部分结果
            return chunks, first_token_time

        return chunks, first_token_time

    async def _check_ollama_service(self, base_url: str, model_name: str) -> bool:
        """异步检查 Ollama 服务状态"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/api/version") as response:
                    if response.status != 200:
                        print(f"Ollama 服务未启动或无法访问: {base_url}")
                        return False
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        if not any(model["name"] == model_name for model in models):
                            print(
                                f"Ollama 模型 {model_name} 未找到，请先使用 `ollama pull {model_name}` 下载"
                            )
                            return False
                    else:
                        print("无法获取 Ollama 模型列表")
                        return False
                return True
            except Exception as e:
                print(f"无法连接到 Ollama 服务: {str(e)}")
                return False

    async def _test_single_sentence(
        self, llm_name: str, llm, sentence: str
    ) -> Optional[Dict]:
        """测试单个句子的性能"""
        try:
            print(f"{llm_name} 开始测试: {sentence[:20]}...")
            sentence_start = time.time()
            first_token_received = False
            first_token_time = None

            # 构建包含系统提示词的消息
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": sentence},
            ]

            # 使用asyncio.wait_for进行超时控制
            try:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # 创建响应收集任务
                    future = executor.submit(
                        self._collect_response_sync,
                        llm,
                        messages,
                        llm_name,
                        sentence_start,
                    )

                    # 使用asyncio.wait_for实现超时控制
                    try:
                        response_chunks, first_token_time = await asyncio.wait_for(
                            asyncio.wrap_future(future), timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        print(f"{llm_name} 测试超时（10秒），跳过")
                        # 强制取消future
                        future.cancel()
                        # 等待一小段时间确保线程池任务能够响应取消
                        try:
                            await asyncio.wait_for(
                                asyncio.wrap_future(future), timeout=1.0
                            )
                        except (
                            asyncio.TimeoutError,
                            concurrent.futures.CancelledError,
                            Exception,
                        ):
                            # 忽略所有异常，确保程序继续执行
                            pass
                        return None

            except Exception as timeout_error:
                print(f"{llm_name} 处理异常: {timeout_error}")
                return None

            response_time = time.time() - sentence_start
            print(f"{llm_name} 完成响应: {response_time:.3f}s")

            return {
                "name": llm_name,
                "type": "llm",
                "first_token_time": first_token_time,
                "response_time": response_time,
            }
        except Exception as e:
            error_msg = str(e).lower()
            # 检查是否为502错误或网络错误
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
            ):
                print(f"{llm_name} 遇到502错误，跳过测试")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "502网络错误",
                }
            print(f"{llm_name} 句子测试失败: {str(e)}")
            return None

    async def _test_llm(self, llm_name: str, config: Dict) -> Dict:
        """异步测试单个 LLM 性能"""
        try:
            # 对于 Ollama，跳过 api_key 检查并进行特殊处理
            if llm_name == "Ollama":
                base_url = config.get("base_url", "http://localhost:11434")
                model_name = config.get("model_name")
                if not model_name:
                    print("Ollama 未配置 model_name")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "网络错误",
                    }

                if not await self._check_ollama_service(base_url, model_name):
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "网络错误",
                    }
            else:
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"跳过未配置的 LLM: {llm_name}")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "配置错误",
                    }

            # 获取实际类型（兼容旧配置）
            module_type = config.get("type", llm_name)
            llm = create_llm_instance(module_type, config)

            # 统一使用 UTF-8 编码
            test_sentences = [
                s.encode("utf-8").decode("utf-8") for s in self.test_sentences
            ]

            # 创建所有句子的测试任务
            sentence_tasks = []
            for sentence in test_sentences:
                sentence_tasks.append(
                    self._test_single_sentence(llm_name, llm, sentence)
                )

            # 并发执行所有句子测试，并处理可能的异常
            sentence_results = await asyncio.gather(
                *sentence_tasks, return_exceptions=True
            )

            # 处理结果，过滤掉异常和None值
            valid_results = []
            for result in sentence_results:
                if isinstance(result, dict) and result is not None:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    error_msg = str(result).lower()
                    if "502" in error_msg or "bad gateway" in error_msg:
                        print(f"{llm_name} 遇到502错误，跳过该句子测试")
                        return {
                            "name": llm_name,
                            "type": "llm",
                            "errors": 1,
                            "error_type": "502网络错误",
                        }
                    else:
                        print(f"{llm_name} 句子测试异常: {result}")

            if not valid_results:
                print(f"{llm_name} 无有效数据，可能遇到网络问题或配置错误")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络错误",
                }

            # 检查有效结果数量，如果太少则认为测试失败
            if len(valid_results) < len(test_sentences) * 0.3:  # 至少要有30%的成功率
                print(
                    f"{llm_name} 成功测试句子过少({len(valid_results)}/{len(test_sentences)})，可能网络不稳定或接口有问题"
                )
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络错误",
                }

            first_token_times = [
                r["first_token_time"]
                for r in valid_results
                if r.get("first_token_time")
            ]
            response_times = [r["response_time"] for r in valid_results]

            # 过滤异常数据（超出3个标准差的数据）
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
                print(f"LLM {llm_name} 遇到502错误，跳过测试")
            else:
                print(f"LLM {llm_name} 测试失败: {str(e)}")
            error_type = "网络错误"
            if "timeout" in str(e).lower():
                error_type = "超时连接"
            return {
                "name": llm_name,
                "type": "llm",
                "errors": 1,
                "error_type": error_type,
            }

    def _print_results(self):
        """打印测试结果"""
        print("\n" + "=" * 50)
        print("LLM 性能测试结果")
        print("=" * 50)

        if not self.results:
            print("没有可用的测试结果")
            return

        headers = ["模型名称", "平均响应时间(s)", "首Token时间(s)", "成功率", "状态"]
        table_data = []

        # 收集所有数据并分类
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # 正常结果
                avg_response = f"{data['avg_response']:.3f}"
                avg_first_token = (
                    f"{data['avg_first_token']:.3f}"
                    if data["avg_first_token"] > 0
                    else "-"
                )
                success_rate = data.get("success_rate", "N/A")
                status = "✅ 正常"

                # 保存用于排序的值
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
                # 错误结果
                avg_response = "-"
                avg_first_token = "-"
                success_rate = "0/5"

                # 获取具体错误类型
                error_type = data.get("error_type", "网络错误")
                status = f"❌ {error_type}"

                error_results.append(
                    [name, avg_response, avg_first_token, success_rate, status]
                )

        # 按首Token时间升序排序
        valid_results.sort(key=lambda x: x["sort_key"])

        # 将排序后的有效结果转换为表格数据
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

        # 将错误结果添加到表格数据末尾
        table_data.extend(error_results)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("\n测试说明:")
        print("- 测试内容：包含完整系统提示词的智能体对话场景")
        print("- 超时控制：单个请求最大等待时间为10秒")
        print("- 错误处理：自动跳过502错误和网络异常的模型")
        print("- 成功率：成功响应的句子数量/总测试句子数量")
        print("\n测试完成！")

    async def run(self):
        """执行全量异步测试"""
        print("开始筛选可用 LLM 模块...")

        # 创建所有测试任务
        all_tasks = []

        # LLM 测试任务
        if self.config.get("LLM") is not None:
            for llm_name, config in self.config.get("LLM", {}).items():
                # 检查配置有效性
                if llm_name == "CozeLLM":
                    if any(x in config.get("bot_id", "") for x in ["你的"]) or any(
                        x in config.get("user_id", "") for x in ["你的"]
                    ):
                        print(f"LLM {llm_name} 未配置 bot_id/user_id，已跳过")
                        continue
                elif "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"LLM {llm_name} 未配置 api_key，已跳过")
                    continue

                # 对于 Ollama，先检查服务状态
                if llm_name == "Ollama":
                    base_url = config.get("base_url", "http://localhost:11434")
                    model_name = config.get("model_name")
                    if not model_name:
                        print("Ollama 未配置 model_name")
                        continue

                    if not await self._check_ollama_service(base_url, model_name):
                        continue

                print(f"添加 LLM 测试任务: {llm_name}")
                all_tasks.append(self._test_llm(llm_name, config))

        print(f"\n找到 {len(all_tasks)} 个可用 LLM 模块")
        print("\n开始并发测试所有模块...\n")

        # 并发执行所有测试任务，但为每个任务设置独立超时
        async def test_with_timeout(task, timeout=30):
            """为每个测试任务添加超时保护"""
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"测试任务超时（{timeout}秒），跳过")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "超时连接",
                }
            except Exception as e:
                print(f"测试任务异常: {str(e)}")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络错误",
                }

        # 为每个任务包装超时保护
        protected_tasks = [test_with_timeout(task) for task in all_tasks]

        # 并发执行所有测试任务
        all_results = await asyncio.gather(*protected_tasks, return_exceptions=True)

        # 处理结果
        for result in all_results:
            if isinstance(result, dict):
                if result.get("errors") == 0:
                    self.results[result["name"]] = result
                else:
                    # 即使有错误也记录，用于显示失败状态
                    if result.get("name") != "Unknown":
                        self.results[result["name"]] = result
            elif isinstance(result, Exception):
                print(f"测试结果处理异常: {str(result)}")

        # 打印结果
        print("\n生成测试报告...")
        self._print_results()


async def main():
    config = await load_config()
    tester = LLMPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
