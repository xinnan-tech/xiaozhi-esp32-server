import asyncio
import logging
import os
import time
import concurrent.futures
from typing import Dict, Optional
import aiohttp
from tabulate import tabulate
from core.utils.asr import create_instance as create_stt_instance

# 设置全局日志级别为WARNING，抑制INFO级别日志
logging.basicConfig(level=logging.WARNING)

description = "语音识别模型性能测试"

class ASRPerformanceTester:
    def __init__(self):
        self.config = self._load_config_from_data_dir()
        self.test_wav_list = self._load_test_wav_files()
        self.results = {"stt": {}}
        
        # 调试日志
        print(f"[DEBUG] 加载的ASR配置: {self.config.get('ASR', {})}")
        print(f"[DEBUG] 音频文件数量: {len(self.test_wav_list)}")

    def _load_config_from_data_dir(self) -> Dict:
        """从 data 目录加载所有 .config.yaml 文件的配置"""
        config = {"ASR": {}}
        data_dir = os.path.join(os.getcwd(), "data")
        print(f"[DEBUG] 扫描配置文件目录: {data_dir}")

        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".config.yaml"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            import yaml
                            file_config = yaml.safe_load(f)
                            # 兼容大小写的 ASR/asr 配置
                            asr_config = file_config.get("ASR") or file_config.get("asr")
                            if asr_config:
                                config["ASR"].update(asr_config)
                                print(f"[DEBUG] 从 {file_path} 加载 ASR 配置成功")
                    except Exception as e:
                        print(f" 加载配置文件 {file_path} 失败: {str(e)}")
        return config

    def _load_test_wav_files(self) -> list:
        """加载测试用的音频文件（添加路径调试）"""
        wav_root = os.path.join(os.getcwd(), "config", "assets")
        print(f"[DEBUG] 音频文件目录: {wav_root}")
        test_wav_list = []
        
        if os.path.exists(wav_root):
            file_list = os.listdir(wav_root)
            print(f"[DEBUG] 找到音频文件: {file_list}")
            for file_name in file_list:
                file_path = os.path.join(wav_root, file_name)
                if os.path.getsize(file_path) > 300 * 1024:  # 300KB
                    with open(file_path, "rb") as f:
                        test_wav_list.append(f.read())
        else:
            print(f" 目录不存在: {wav_root}")
        return test_wav_list

    async def _test_single_audio(self, stt_name: str, stt, audio_data: bytes) -> Optional[float]:
        """测试单个音频文件的性能"""
        try:
            start_time = time.time()
            text, _ = await stt.speech_to_text_wrapper([audio_data], "1", stt.audio_format)
            if text is None:
                return None
            
            duration = time.time() - start_time
            
            # 检测0.000s的异常时间
            if abs(duration) < 0.001:  # 小于1毫秒视为异常
                print(f"{stt_name} 检测到异常时间: {duration:.6f}s (视为错误)")
                return None
                
            return duration
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                print(f"{stt_name} 遇到502错误")
                return None
            return None

    async def _test_stt_with_timeout(self, stt_name: str, config: Dict) -> Dict:
        """异步测试单个STT性能，带超时控制"""
        try:
            # 检查配置有效性
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and str(config[field]).lower() in ["你的", "placeholder", "none", "null", ""]
                for field in token_fields
            ):
                print(f"  STT {stt_name} 未配置有效access_token/api_key，已跳过")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "配置错误"
                }

            module_type = config.get("type", stt_name)
            stt = create_stt_instance(module_type, config, delete_audio_file=True)
            stt.audio_format = "pcm"

            print(f" 测试 STT: {stt_name}")

            # 使用线程池和超时控制
            loop = asyncio.get_event_loop()
            
            # 测试第一个音频文件作为连通性检查
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self._test_single_audio(stt_name, stt, self.test_wav_list[0]))
                    )
                    first_result = await asyncio.wait_for(
                        asyncio.wrap_future(future), timeout=10.0
                    )
                    
                    if first_result is None:
                        print(f" {stt_name} 连接失败")
                        return {
                            "name": stt_name,
                            "type": "stt",
                            "errors": 1,
                            "error_type": "网络错误"
                        }
            except asyncio.TimeoutError:
                print(f" {stt_name} 连接超时（10秒），跳过")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "超时连接"
                }
            except Exception as e:
                error_msg = str(e).lower()
                if "502" in error_msg or "bad gateway" in error_msg:
                    print(f" {stt_name} 遇到502错误，跳过")
                    return {
                        "name": stt_name,
                        "type": "stt",
                        "errors": 1,
                        "error_type": "502网络错误"
                    }
                print(f" {stt_name} 连接异常: {str(e)}")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络错误"
                }

                       # 全量测试，带超时控制
            total_time = 0
            valid_tests = 0
            test_count = len(self.test_wav_list)
            
            for i, audio_data in enumerate(self.test_wav_list, 1):
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(self._test_single_audio(stt_name, stt, audio_data))
                        )
                        duration = await asyncio.wait_for(
                            asyncio.wrap_future(future), timeout=10.0
                        )
                        
                        if duration is not None and duration > 0.001:  
                            total_time += duration
                            valid_tests += 1
                            print(f" {stt_name} [{i}/{test_count}] 耗时: {duration:.2f}s")
                        else:
                            print(f" {stt_name} [{i}/{test_count}] 测试失败(含0.000s异常)")
                            
                except asyncio.TimeoutError:
                    print(f" {stt_name} [{i}/{test_count}] 超时（10秒），跳过")
                    continue
                except Exception as e:
                    error_msg = str(e).lower()
                    if "502" in error_msg or "bad gateway" in error_msg:
                        print(f" {stt_name} [{i}/{test_count}] 502错误，跳过")
                        return {
                            "name": stt_name,
                            "type": "stt",
                            "errors": 1,
                            "error_type": "502网络错误"
                        }
                    print(f" {stt_name} [{i}/{test_count}] 异常: {str(e)}")
                    continue
            # 检查有效测试数量
            if valid_tests < test_count * 0.3:  # 至少30%成功率
                print(f" {stt_name} 成功测试过少({valid_tests}/{test_count})，可能网络不稳定")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络错误"
                }

            if valid_tests == 0:
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络错误"
                }

            avg_time = total_time / valid_tests
            return {
                "name": stt_name,
                "type": "stt",
                "avg_time": avg_time,
                "success_rate": f"{valid_tests}/{test_count}",
                "errors": 0,
            }

        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                error_type = "502网络错误"
            elif "timeout" in error_msg:
                error_type = "超时连接"
            else:
                error_type = "网络错误"
            print(f"⚠️ {stt_name} 测试失败: {str(e)}")
            return {
                "name": stt_name,
                "type": "stt",
                "errors": 1,
                "error_type": error_type
            }

    def _print_results(self):
        """打印测试结果，按响应时间排序"""
        print("\n" + "=" * 50)
        print("ASR 性能测试结果")
        print("=" * 50)

        if not self.results.get("stt"):
            print("没有可用的测试结果")
            return

        headers = ["模型名称", "平均耗时(s)", "成功率", "状态"]
        table_data = []

        # 收集所有数据并分类
        valid_results = []
        error_results = []

        for name, data in self.results["stt"].items():
            if data["errors"] == 0:
                # 正常结果
                avg_time = f"{data['avg_time']:.3f}"
                success_rate = data.get("success_rate", "N/A")
                status = "✅ 正常"
                
                # 保存用于排序的值
                sort_key = data["avg_time"]
                
                valid_results.append({
                    "name": name,
                    "avg_time": avg_time,
                    "success_rate": success_rate,
                    "status": status,
                    "sort_key": sort_key,
                })
            else:
                # 错误结果
                avg_time = "-"
                success_rate = "0/N"
                
                # 获取具体错误类型
                error_type = data.get("error_type", "网络错误")
                status = f"❌ {error_type}"
                
                error_results.append([name, avg_time, success_rate, status])

        # 按响应时间升序排序（从快到慢）
        valid_results.sort(key=lambda x: x["sort_key"])

        # 将排序后的有效结果转换为表格数据
        for result in valid_results:
            table_data.append([
                result["name"],
                result["avg_time"],
                result["success_rate"],
                result["status"],
            ])

        # 将错误结果添加到表格数据末尾
        table_data.extend(error_results)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("\n测试说明:")
        print("- 超时控制：单个音频最大等待时间为10秒")
        print("- 错误处理：自动跳过502错误、超时和网络异常的模型")
        print("- 成功率：成功识别的音频数量/总测试音频数量")
        print("- 排序规则：按平均耗时从快到慢排序，错误模型排最后")
        print("\n测试完成！")

    async def run(self):
        """执行全量异步测试""" 
        print("开始筛选可用ASR模块...")
        if not self.config.get("ASR"):
            print("配置中未找到 ASR 模块")
            return

        all_tasks = []
        for stt_name, config in self.config["ASR"].items():
            # 检查配置有效性
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and str(config[field]).lower() in ["你的", "placeholder", "none", "null", ""]
                for field in token_fields
            ):
                print(f"ASR {stt_name} 未配置有效access_token/api_key，已跳过")
                continue
            
            print(f"添加 ASR 测试任务: {stt_name}")
            all_tasks.append(self._test_stt_with_timeout(stt_name, config))

        if not all_tasks:
            print("没有可用的ASR模块进行测试。")
            return

        print(f"\n找到 {len(all_tasks)} 个可用ASR模块")
        print("\n开始并发测试所有ASR模块...")
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # 处理结果
        for result in all_results:
            if isinstance(result, dict) and result.get("type") == "stt":
                self.results["stt"][result["name"]] = result

        # 打印结果
        self._print_results()


async def main():
    tester = ASRPerformanceTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())