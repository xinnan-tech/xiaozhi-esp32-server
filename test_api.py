import asyncio
import aiohttp
import requests
import time
import random
import string
import logging
import argparse
import json
import concurrent.futures
import emoji
from pathlib import Path
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 测试配置
class TestConfig:
    def __init__(self, base_url: str = "http://localhost:9881"):
        self.base_url = base_url
        self.output_dir = Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # 测试强度配置
        self.concurrent_requests = 10  # 并发请求数
        self.stress_test_duration = 60  # 压力测试持续时间(秒)
        self.request_timeout = 30  # 请求超时时间(秒)
        
        # 批量测试配置
        self.batch_size = 5  # 批处理大小
        
        # 缓存测试结果
        self.test_results = []
        
        # 已缓存的speaker列表
        self.speakers = None

# 异常输入生成器
class AbnormalInputGenerator:
    @staticmethod
    def get_emoji_text(count: int = 5) -> str:
        """生成包含表情符号的文本"""
        emojis = list(emoji.EMOJI_DATA.keys())
        sample = random.sample(emojis, min(count, len(emojis)))
        return "这是一段" + "".join(sample) + "包含表情符号的测试文本"
    
    @staticmethod
    def get_long_text(length: int = 2000) -> str:
        """生成超长文本"""
        return "这是一段非常长的测试文本。" * (length // 10)
    
    @staticmethod
    def get_special_chars() -> str:
        """生成包含特殊字符的文本"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?\\`~"
        return f"包含特殊字符的文本：{special_chars}"
    
    @staticmethod
    def get_control_chars() -> str:
        """生成包含控制字符的文本"""
        control_chars = ''.join(chr(i) for i in range(32) if i not in (9, 10, 13))
        return f"正常文本{control_chars}包含控制字符"
    
    @staticmethod
    def get_mixed_language() -> str:
        """生成混合语言文本"""
        return "这是中文 This is English こんにちは 안녕하세요 Привет"
    
    @staticmethod
    def get_repeated_chars() -> str:
        """生成重复字符文本"""
        return "啊" * 50 + "测试重复字符"
    
    @staticmethod
    def get_html_injection() -> str:
        """生成包含HTML注入的文本"""
        return "正常文本<script>alert('XSS')</script><img src=x onerror=alert('XSS')>"
    
    @staticmethod
    def get_sql_injection() -> str:
        """生成包含SQL注入的文本"""
        return "正常文本'; DROP TABLE users; --"
    
    @staticmethod
    def get_zero_width_chars() -> str:
        """生成包含零宽字符的文本"""
        zero_width_chars = '\u200b\u200c\u200d\ufeff'
        return f"包含零宽字符的文本：{''.join(c + z for c, z in zip('测试文本', zero_width_chars))}"
    
    @staticmethod
    def get_abnormal_inputs() -> List[Dict[str, str]]:
        """获取所有异常输入及其描述"""
        return [
            {"description": "表情符号文本", "text": AbnormalInputGenerator.get_emoji_text()},
            {"description": "超长文本", "text": AbnormalInputGenerator.get_long_text()},
            {"description": "特殊字符", "text": AbnormalInputGenerator.get_special_chars()},
            {"description": "控制字符", "text": AbnormalInputGenerator.get_control_chars()},
            {"description": "混合语言", "text": AbnormalInputGenerator.get_mixed_language()},
            {"description": "重复字符", "text": AbnormalInputGenerator.get_repeated_chars()},
            {"description": "HTML注入", "text": AbnormalInputGenerator.get_html_injection()},
            {"description": "SQL注入", "text": AbnormalInputGenerator.get_sql_injection()},
            {"description": "零宽字符", "text": AbnormalInputGenerator.get_zero_width_chars()},
            {"description": "空文本", "text": ""},
            {"description": "单个字符", "text": "我"},
        ]

# API测试类
class CosyVoiceAPITester:
    def __init__(self, config: TestConfig):
        self.config = config
        self.session = requests.Session()
        
    def get_speakers(self) -> List[str]:
        """获取可用的音色列表"""
        if self.config.speakers is not None:
            return self.config.speakers
            
        try:
            response = self.session.get(f"{self.config.base_url}/speakers", timeout=self.config.request_timeout)
            response.raise_for_status()
            speakers = response.json().get("speakers", [])
            self.config.speakers = speakers
            return speakers
        except Exception as e:
            logging.error(f"获取音色列表失败: {str(e)}")
            return []
            
    def get_random_speaker(self) -> Optional[str]:
        """获取随机音色"""
        speakers = self.get_speakers()
        if not speakers:
            return None
        return random.choice(speakers)
    
    def test_root_endpoint(self) -> Dict[str, Any]:
        """测试根端点"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.config.base_url}/", timeout=self.config.request_timeout)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def test_status_endpoint(self) -> Dict[str, Any]:
        """测试状态端点"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.config.base_url}/status", timeout=self.config.request_timeout)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def test_tts_endpoint(self, text: str, description: str = "正常测试") -> Dict[str, Any]:
        """测试TTS端点"""
        speaker = self.get_random_speaker()
        if not speaker:
            return {"success": False, "error": "没有可用的音色"}
            
        start_time = time.time()
        try:
            data = {
                "text": text,
                "mode": "预训练音色",
                "speaker": speaker,
                "seed": random.randint(0, 10000),
                "stream": False,
                "speed": random.uniform(0.8, 1.2)
            }
            
            response = self.session.post(
                f"{self.config.base_url}/tts", 
                data=data,
                timeout=self.config.request_timeout
            )
            
            # 检查响应类型
            if response.headers.get("Content-Type") == "application/json":
                # 发生错误，API返回了JSON错误信息
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response_time": time.time() - start_time,
                    "description": description,
                    "text": text,
                    "error": response.json()
                }
            else:
                # 成功获取音频
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": time.time() - start_time,
                    "description": description,
                    "text": text,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": len(response.content)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "description": description,
                "text": text
            }
    
    def test_stream_tts_endpoint(self, text: str, description: str = "流式测试") -> Dict[str, Any]:
        """测试流式TTS端点"""
        speaker = self.get_random_speaker()
        if not speaker:
            return {"success": False, "error": "没有可用的音色"}
            
        start_time = time.time()
        try:
            params = {
                "text": text,
                "mode": "预训练音色",
                "speaker": speaker,
                "seed": random.randint(0, 10000),
                "speed": random.uniform(0.8, 1.2)
            }
            
            response = self.session.get(
                f"{self.config.base_url}/stream_tts", 
                params=params,
                stream=True,
                timeout=self.config.request_timeout
            )
            
            # 检查响应类型
            if response.headers.get("Content-Type") == "application/json":
                # 发生错误，API返回了JSON错误信息
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response_time": time.time() - start_time,
                    "description": description,
                    "text": text,
                    "error": response.json()
                }
            else:
                # 成功获取流式音频
                content_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    content_size += len(chunk)
                    
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": time.time() - start_time,
                    "description": description,
                    "text": text,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": content_size
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "description": description,
                "text": text
            }
    
    def test_invalid_speaker(self) -> Dict[str, Any]:
        """测试无效的音色"""
        invalid_speaker = "不存在的音色" + str(random.randint(1000, 9999))
        start_time = time.time()
        try:
            data = {
                "text": "测试无效音色",
                "mode": "预训练音色",
                "speaker": invalid_speaker,
                "seed": random.randint(0, 10000),
                "stream": False
            }
            
            response = self.session.post(
                f"{self.config.base_url}/tts", 
                data=data,
                timeout=self.config.request_timeout
            )
            
            return {
                "success": response.status_code == 400,  # 期望返回400
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
                "description": "无效音色测试",
                "data": response.json() if response.headers.get("Content-Type") == "application/json" else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "description": "无效音色测试"
            }
    
    def test_abnormal_inputs(self) -> List[Dict[str, Any]]:
        """测试各种异常输入"""
        results = []
        abnormal_inputs = AbnormalInputGenerator.get_abnormal_inputs()
        
        for input_data in abnormal_inputs:
            result = self.test_tts_endpoint(
                text=input_data["text"],
                description=input_data["description"]
            )
            results.append(result)
            time.sleep(0.5)  # 避免过快请求
            
        return results
    
    def test_invalid_mode(self) -> Dict[str, Any]:
        """测试无效的模式"""
        invalid_mode = "不存在的模式" + str(random.randint(1000, 9999))
        start_time = time.time()
        try:
            data = {
                "text": "测试无效模式",
                "mode": invalid_mode,
                "speaker": self.get_random_speaker(),
                "seed": random.randint(0, 10000),
                "stream": False
            }
            
            response = self.session.post(
                f"{self.config.base_url}/tts", 
                data=data,
                timeout=self.config.request_timeout
            )
            
            return {
                "success": response.status_code in (400, 422),  # 期望返回错误
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
                "description": "无效模式测试",
                "data": response.json() if response.headers.get("Content-Type") == "application/json" else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "description": "无效模式测试"
            }

# 异步压力测试工具
class StressTestTool:
    def __init__(self, config: TestConfig):
        self.config = config
        
    async def fetch(self, session, url, data=None, method="GET", params=None):
        """发送异步HTTP请求"""
        start_time = time.time()
        try:
            if method.upper() == "POST":
                async with session.post(url, data=data, timeout=self.config.request_timeout) as response:
                    await response.read()
                    return {
                        "success": response.status == 200,
                        "status_code": response.status,
                        "response_time": time.time() - start_time
                    }
            else:
                async with session.get(url, params=params, timeout=self.config.request_timeout) as response:
                    await response.read()
                    return {
                        "success": response.status == 200,
                        "status_code": response.status,
                        "response_time": time.time() - start_time
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    async def run_stress_test(self, endpoint: str, duration: int, concurrency: int, method="GET", data_generator=None):
        """运行压力测试"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            end_time = start_time + duration
            tasks = []
            results = []
            
            while time.time() < end_time:
                # 创建并发任务
                for _ in range(concurrency):
                    if method.upper() == "POST":
                        data = data_generator() if data_generator else None
                        task = asyncio.create_task(
                            self.fetch(session, f"{self.config.base_url}{endpoint}", data=data, method="POST")
                        )
                    else:
                        task = asyncio.create_task(
                            self.fetch(session, f"{self.config.base_url}{endpoint}", method="GET")
                        )
                    tasks.append(task)
                
                # 等待所有任务完成
                for task in tasks:
                    result = await task
                    results.append(result)
                
                tasks = []
                await asyncio.sleep(0.1)  # 稍微暂停以避免过载
            
            # 计算统计信息
            success_count = sum(1 for r in results if r.get("success", False))
            success_rate = success_count / len(results) if results else 0
            response_times = [r.get("response_time", 0) for r in results if "response_time" in r]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "concurrency": concurrency,
                "total_requests": len(results),
                "success_requests": success_count,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0
            }

# 测试函数
async def run_tests(config: TestConfig):
    """运行所有测试"""
    tester = CosyVoiceAPITester(config)
    stress_tool = StressTestTool(config)
    
    logging.info("开始测试CosyVoice API...")
    
    # 1. 基本端点测试
    logging.info("测试基本端点...")
    root_result = tester.test_root_endpoint()
    status_result = tester.test_status_endpoint()
    
    # 2. 异常输入测试
    logging.info("测试异常输入...")
    abnormal_results = tester.test_abnormal_inputs()
    
    # 3. 无效参数测试
    logging.info("测试无效参数...")
    invalid_speaker_result = tester.test_invalid_speaker()
    invalid_mode_result = tester.test_invalid_mode()
    
    # 4. 压力测试
    logging.info(f"开始压力测试，持续{config.stress_test_duration}秒...")
    
    # TTS端点压力测试
    def generate_tts_data():
        speaker = tester.get_random_speaker()
        return {
            "text": f"这是一个压力测试用例 {random.randint(1, 1000)}",
            "mode": "预训练音色",
            "speaker": speaker,
            "seed": random.randint(0, 10000),
            "stream": random.choice([True, False]),
            "speed": random.uniform(0.8, 1.2)
        }
    
    tts_stress_result = await stress_tool.run_stress_test(
        endpoint="/tts",
        duration=config.stress_test_duration,
        concurrency=config.concurrent_requests,
        method="POST",
        data_generator=generate_tts_data
    )
    
    # 状态端点压力测试
    status_stress_result = await stress_tool.run_stress_test(
        endpoint="/status",
        duration=min(10, config.stress_test_duration),  # 状态端点压力测试时间较短
        concurrency=config.concurrent_requests,
        method="GET"
    )
    
    # 汇总结果
    results = {
        "basic_endpoints": {
            "root": root_result,
            "status": status_result
        },
        "abnormal_inputs": abnormal_results,
        "invalid_parameters": {
            "invalid_speaker": invalid_speaker_result,
            "invalid_mode": invalid_mode_result
        },
        "stress_tests": {
            "tts": tts_stress_result,
            "status": status_stress_result
        }
    }
    
    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = config.output_dir / f"test_results_{timestamp}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.info(f"测试完成，结果已保存至 {result_file}")
    
    # 打印摘要
    logging.info("测试摘要:")
    logging.info(f"基本端点测试: root {'成功' if root_result.get('success') else '失败'}, status {'成功' if status_result.get('success') else '失败'}")
    logging.info(f"异常输入测试: {sum(1 for r in abnormal_results if r.get('success'))} 成功, {sum(1 for r in abnormal_results if not r.get('success'))} 失败")
    logging.info(f"TTS压力测试: 总请求 {tts_stress_result['total_requests']}, 成功率 {tts_stress_result['success_rate']*100:.2f}%, 平均响应时间 {tts_stress_result['avg_response_time']:.2f}s")
    
    return results

# 添加一个更激进的高压力测试函数
async def run_aggressive_stress_test(config: TestConfig):
    """运行更激进的压力测试，尝试找出API服务的极限"""
    stress_tool = StressTestTool(config)
    tester = CosyVoiceAPITester(config)
    
    logging.info("开始进行极限压力测试...")
    
    # 准备一些短文本以减少处理时间
    short_texts = [
        "这是一个简短的测试文本。",
        "测试语音合成系统。",
        "快速压力测试用例。",
        "简短句子测试。",
    ]
    
    def generate_quick_tts_data():
        """生成简短文本的TTS请求数据"""
        speaker = tester.get_random_speaker()
        return {
            "text": random.choice(short_texts),
            "mode": "预训练音色",
            "speaker": speaker,
            "seed": random.randint(0, 10000),
            "stream": True,  # 使用流式处理可能更快
            "speed": 1.2  # 稍微加快语速
        }
    
    # 测试不同并发级别下的性能
    concurrency_levels = [5, 10, 20, 30, 50]
    duration = 15  # 每个级别测试15秒
    
    results = []
    for concurrency in concurrency_levels:
        logging.info(f"测试并发级别: {concurrency}")
        
        result = await stress_tool.run_stress_test(
            endpoint="/tts",
            duration=duration,
            concurrency=concurrency,
            method="POST",
            data_generator=generate_quick_tts_data
        )
        
        results.append({
            "concurrency": concurrency,
            **result
        })
        
        # 暂停一段时间让服务器恢复
        await asyncio.sleep(5)
    
    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = config.output_dir / f"extreme_stress_test_{timestamp}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logging.info(f"极限压力测试完成，结果已保存至 {result_file}")
    
    # 打印摘要
    logging.info("极限压力测试摘要:")
    for r in results:
        logging.info(f"并发数: {r['concurrency']}, 总请求: {r['total_requests']}, " 
                    f"成功率: {r['success_rate']*100:.2f}%, "
                    f"平均响应时间: {r['avg_response_time']:.2f}s")
    
    return results

# 主函数
async def main():
    parser = argparse.ArgumentParser(description="CosyVoice API测试工具")
    parser.add_argument("--base-url", default="http://localhost:9881", help="API服务基础URL")
    parser.add_argument("--duration", type=int, default=60, help="压力测试持续时间(秒)")
    parser.add_argument("--concurrency", type=int, default=10, help="并发请求数")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时时间(秒)")
    parser.add_argument("--extreme-test", action="store_true", 
                      help="运行极限压力测试")
    args = parser.parse_args()
    
    config = TestConfig(base_url=args.base_url)
    config.stress_test_duration = args.duration
    config.concurrent_requests = args.concurrency
    config.request_timeout = args.timeout
    
    if args.extreme_test:
        await run_aggressive_stress_test(config)
    else:
        await run_tests(config)

if __name__ == "__main__":
    asyncio.run(main()) 