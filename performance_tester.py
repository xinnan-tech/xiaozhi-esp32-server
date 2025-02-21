import time
from tabulate import tabulate
from typing import Dict
from core.utils.llm import create_instance as create_llm_instance
from core.utils.tts import create_instance as create_tts_instance
from core.utils.util import read_config
import statistics
from config.settings import get_config_file
from concurrent.futures import ThreadPoolExecutor
import inspect
import os
import requests
import logging

# 设置全局日志级别为WARNING，抑制INFO级别日志
logging.basicConfig(level=logging.WARNING)

class PerformanceTester:
    def __init__(self):
        self.config = read_config(get_config_file())
        # 从配置读取测试句子，如果不存在则使用默认
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences", 
            ["你好，请介绍一下你自己", "What's the weather like today?", 
             "请用100字概括量子计算的基本原理和应用前景"]
        )
        self.results = {
            "llm": {},
            "tts": {},
            "combinations": []
        }

    def _test_llm(self, llm_name: str, config: Dict) -> Dict:
        """测试单个LLM性能"""
        try:
            # 跳过未配置密钥的模块
            if "api_key" in config and any(x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]):
                print(f"🚫 跳过未配置的LLM: {llm_name}")
                return {"errors": 1}
            
            # 获取实际类型（兼容旧配置）
            module_type = config.get('type', llm_name)
            llm = create_llm_instance(module_type, config)
            
            # 统一使用UTF-8编码
            test_sentences = [s.encode('utf-8').decode('utf-8') for s in self.test_sentences]
            
            total_time = 0
            first_token_times = []
            valid_times = []
            
            for sentence in test_sentences:
                sentence_start = time.time()  # 记录整句开始时间
                first_token_received = False
                
                # 遍历响应流
                for chunk in llm.response("perf_test", [{"role": "user", "content": sentence}]):
                    if not first_token_received and chunk.strip() != '':
                        first_token_times.append(time.time() - sentence_start)
                        first_token_received = True
                
                # 计算整句耗时
                sentence_duration = time.time() - sentence_start
                total_time += sentence_duration
                valid_times.append(sentence_duration)
            
            # 新增有效性检查
            if len(first_token_times) == 0 or len(valid_times) == 0:
                print(f"⚠️  {llm_name} 无有效数据，可能配置错误")
                return {"errors": 1}
                
            # 过滤异常数据（超过3倍标准差）
            mean = statistics.mean(valid_times)
            stdev = statistics.stdev(valid_times) if len(valid_times) > 1 else 0
            filtered_times = [t for t in valid_times if t <= mean + 3*stdev]
            
            # 当有效数据不足时标记错误
            if len(filtered_times) < len(test_sentences) * 0.5:
                print(f"⚠️  {llm_name} 有效数据不足，可能网络不稳定")
                return {"errors": 1}

            return {
                "avg_response": total_time / len(test_sentences),
                "avg_first_token": sum(first_token_times)/len(first_token_times),
                "std_first_token": statistics.stdev(first_token_times) if len(first_token_times) > 1 else 0,
                "std_response": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
                "errors": 0
            }
        except Exception as e:
            print(f"LLM {llm_name} 测试失败: {str(e)}")
            return {"errors": 1}

    def _test_tts(self, tts_name: str, config: Dict) -> Dict:
        """测试单个TTS性能"""
        try:
            # 关闭详细日志
            logging.getLogger("core.providers.tts.base").setLevel(logging.WARNING)
            
            # 跳过未配置密钥的模块
            token_fields = ["access_token", "api_key", "token"]
            if any(field in config and any(x in config[field] for x in ["你的", "placeholder"]) for field in token_fields):
                print(f"⏭️  TTS {tts_name} 未配置access_token/api_key，已跳过")
                return {"errors": 1}
            
            # 获取实际类型（兼容旧配置）
            module_type = config.get('type', tts_name)
            tts = create_tts_instance(
                module_type,
                config, 
                delete_audio_file=True  # 确保参数名称正确
            )
            
            # 简化后的输出
            print(f"\n🎵 正在测试 TTS: {tts_name}")
            print(f"🔊 测试 {tts_name}：", end="", flush=True)
            
            # 连接测试
            test_conn = tts.to_tts("连接测试")
            if not os.path.exists(test_conn):
                print("❌ 连接失败")
                return {"errors": 1}
            else:
                print("✅")
    
            total_time = 0
            test_count = len(self.test_sentences[:2])
            
            for i, sentence in enumerate(self.test_sentences[:2], 1):
                start = time.time()
                file_path = tts.to_tts(sentence)
                duration = time.time() - start
                total_time += duration
                
                # 显示简单的进度标识
                if os.path.exists(file_path):
                    print(f"✓[{i}/{test_count}]", end="", flush=True)
                else:
                    print(f"✗[{i}/{test_count}]", end="", flush=True)
            
            print()  # 换行
            return {"avg_time": total_time / test_count, "errors": 0}
    
        except requests.exceptions.ConnectionError:
            print(f"\n⛔ {tts_name} 无法连接服务端")
            return {"errors": 1}
        except Exception as e:
            print(f"\n⚠️ {tts_name} 测试失败: {str(e)}")
            return {"errors": 1}

    def run(self):
        """执行全量测试并自动跳过未配置的模块"""
        print("🔍 开始自动检测已配置的模块...")
        
        # 测试所有LLM
        for llm_name, config in self.config.get("LLM", {}).items():
            # 特殊处理CozeLLM的配置检查
            if llm_name == "CozeLLM":
                if any(x in config.get("bot_id", "") for x in ["你的"]) \
                or any(x in config.get("user_id", "") for x in ["你的"]):
                    print(f"⏭️  LLM {llm_name} 未配置bot_id/user_id，已跳过")
                    continue
            # 通用的api_key配置检查
            if "api_key" in config and any(x in config["api_key"] for x in ["你的", "placeholder"]):
                print(f"⏭️  LLM {llm_name} 未配置api_key，已跳过")
                continue
                
            print(f"🚀 正在测试 LLM: {llm_name}")
            self.results["llm"][llm_name] = self._test_llm(llm_name, config)
        
        # 测试所有TTS
        for tts_name, config in self.config.get("TTS", {}).items():
            # 根据不同服务的token字段检测
            token_fields = ["access_token", "api_key", "token"]
            if any(field in config and any(x in config[field] for x in ["你的", "placeholder"]) for field in token_fields):
                print(f"⏭️  TTS {tts_name} 未配置access_token/api_key，已跳过")
                continue
                
            print(f"🎵 正在测试 TTS: {tts_name}")
            self.results["tts"][tts_name] = self._test_tts(tts_name, config)
        
        # 生成组合建议
        self._generate_combinations()
        self._print_results()

    def _generate_combinations(self):
        """生成最佳组合建议"""
        # 调整过滤条件，例如设为 >= 0.05
        valid_llms = [
            k for k, v in self.results["llm"].items() 
            if v["errors"] == 0 and v["avg_first_token"] >= 0.05
        ]
        valid_tts = [k for k, v in self.results["tts"].items() if v["errors"] == 0]

        for llm in valid_llms:
            for tts in valid_tts:
                llm_weight = 0.8 if self.results["llm"][llm]["avg_first_token"] < 1.0 else 0.6
                tts_weight = 1 - llm_weight
                score = (
                    self.results["llm"][llm]["avg_first_token"] * llm_weight +
                    self.results["tts"][tts]["avg_time"] * tts_weight
                )
                self.results["combinations"].append({
                    "llm": llm,
                    "tts": tts,
                    "score": score,
                    "details": {
                        "llm_first_token": self.results["llm"][llm]["avg_first_token"],
                        "tts_time": self.results["tts"][tts]["avg_time"]
                    }
                })

        # 按综合得分排序
        self.results["combinations"].sort(key=lambda x: x["score"])

    def _print_results(self):
        """控制台输出结果"""
        # LLM结果表格
        llm_table = []
        for name, data in self.results["llm"].items():
            if data["errors"] == 0:
                llm_table.append([
                    name,
                    f"{data['avg_first_token']:.3f}s",
                    f"{data['avg_response']:.3f}s"
                ])

        if llm_table:
            print("\nLLM 性能排行:")
            print(tabulate(
                llm_table,
                headers=["模块名称", "平均首Token时间", "平均总响应时间"],
                tablefmt="github"
            ))
        else:
            print("\n⚠️ 没有可用的LLM模块进行测试。")

        # TTS结果表格
        tts_table = []
        for name, data in self.results["tts"].items():
            if data["errors"] == 0:
                tts_table.append([
                    name,
                    f"{data['avg_time']:.3f}s"
                ])

        if tts_table:
            print("\nTTS 性能排行:")
            print(tabulate(
                tts_table,
                headers=["模块名称", "平均合成时间"],
                tablefmt="github"
            ))
        else:
            print("\n⚠️ 没有可用的TTS模块进行测试。")

        # 最佳组合建议
        if self.results["combinations"]:
            print("\n推荐配置组合 (综合响应速度):")
            combo_table = []
            for combo in self.results["combinations"][:5]:  # 显示前5名
                combo_table.append([
                    f"{combo['llm']} + {combo['tts']}",
                    f"{combo['score']:.3f}",
                    f"{combo['details']['llm_first_token']:.3f}s",
                    f"{combo['details']['tts_time']:.3f}s"
                ])
            
            print(tabulate(
                combo_table,
                headers=["组合方案", "综合得分", "LLM首Token", "TTS合成"],
                tablefmt="github"
            ))
        else:
            print("\n⚠️ 没有可用的模块组合建议。")

    def _execute_with_timeout(self, func, args=(), kwargs={}, timeout=None):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                result = future.result(timeout)
                return list(result) if inspect.isgenerator(result) else result
            except TimeoutError:
                raise Exception("操作超时")

if __name__ == "__main__":
    tester = PerformanceTester()
    tester.run()