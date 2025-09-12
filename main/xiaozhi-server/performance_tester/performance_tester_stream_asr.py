import asyncio
import time
import json
import uuid
import os
import websockets
import gzip
import random
from urllib import parse
from tabulate import tabulate
from config.settings import load_config
import tempfile
import wave
description = "流式ASR首词延迟测试"
try:
    import dashscope
except ImportError:
    dashscope = None

class BaseASRTester:
    def __init__(self, config_key: str):
        self.config = load_config()
        self.config_key = config_key
        self.asr_config = self.config.get("ASR", {}).get(config_key, {})
        self.test_audio_files = self._load_test_audio_files()
        self.results = []

    def _load_test_audio_files(self):
        audio_root = os.path.join(os.getcwd(), "config", "assets")
        test_files = []
        if os.path.exists(audio_root):
            for file_name in os.listdir(audio_root):
                if file_name.endswith(('.wav', '.pcm')):
                    file_path = os.path.join(audio_root, file_name)
                    with open(file_path, 'rb') as f:
                        test_files.append({
                            'data': f.read(),
                            'path': file_path,
                            'name': file_name
                        })
        return test_files

    async def test(self, test_count=5):
        raise NotImplementedError

    def _calculate_result(self, service_name, latencies, test_count):
        valid_latencies = [l for l in latencies if l > 0]
        if valid_latencies:
            avg_latency = sum(valid_latencies) / len(valid_latencies)
            status = f"成功（{len(valid_latencies)}/{test_count}次有效）"
        else:
            avg_latency = 0
            status = "失败: 所有测试均失败"
        return {"name": service_name, "latency": avg_latency, "status": status}


class DoubaoStreamASRTester(BaseASRTester):
    def __init__(self):
        super().__init__("DoubaoStreamASR")

    def _generate_header(self):
        header = bytearray()
        header.append((0x01 << 4) | 0x01)
        header.append((0x01 << 4) | 0x00)
        header.append((0x01 << 4) | 0x01)
        header.append(0x00)
        return header

    def _generate_audio_default_header(self):
        return self._generate_header()

    def _parse_response(self, res: bytes) -> dict:
        try:
            if len(res) < 4:
                return {"error": "响应数据长度不足"}
            header = res[:4]
            message_type = header[1] >> 4
            if message_type == 0x0F:
                code = int.from_bytes(res[4:8], "big", signed=False)
                msg_length = int.from_bytes(res[8:12], "big", signed=False)
                error_msg = json.loads(res[12:].decode("utf-8"))
                return {
                    "code": code,
                    "msg_length": msg_length,
                    "payload_msg": error_msg
                }
            try:
                json_data = res[12:].decode("utf-8")
                return {"payload_msg": json.loads(json_data)}
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {"error": "JSON解析失败"}
        except Exception:
            return {"error": "解析响应失败"}

    async def test(self, test_count=5):
        if not self.test_audio_files:
            return {"name": "豆包流式ASR", "latency": 0, "status": "失败: 未找到测试音频"}
        if not self.asr_config:
            return {"name": "豆包流式ASR", "latency": 0, "status": "失败: 未配置"}

        latencies = []
        for i in range(test_count):
            try:
                ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
                appid = self.asr_config["appid"]
                access_token = self.asr_config["access_token"]
                uid = self.asr_config.get("uid", "streaming_asr_service")

                start_time = time.time()

                headers = {
                    "X-Api-App-Key": appid,
                    "X-Api-Access-Key": access_token,
                    "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
                    "X-Api-Connect-Id": str(uuid.uuid4())
                }

                async with websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    max_size=1000000000,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10
                ) as ws:
                    request_params = {
                        "app": {"appid": appid, "token": access_token},
                        "user": {"uid": uid},
                        "request": {
                            "reqid": str(uuid.uuid4()),
                            "workflow": "audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate",
                            "show_utterances": True,
                            "result_type": "single",
                            "sequence": 1
                        },
                        "audio": {
                            "format": "pcm",
                            "codec": "pcm",
                            "rate": 16000,
                            "language": "zh-CN",
                            "bits": 16,
                            "channel": 1,
                            "sample_rate": 16000
                        }
                    }

                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)
                    full_client_request = self._generate_header()
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    full_client_request.extend(payload_bytes)
                    await ws.send(full_client_request)

                    init_res = await ws.recv()
                    result = self._parse_response(init_res)
                    if "code" in result and result["code"] != 1000:
                        raise Exception(f"初始化失败: {result.get('payload_msg', {}).get('error', '未知错误')}")

                    audio_data = self.test_audio_files[0]['data']
                    if audio_data.startswith(b'RIFF'):
                        audio_data = audio_data[44:]

                    payload = gzip.compress(audio_data)
                    audio_request = bytearray(self._generate_audio_default_header())
                    audio_request.extend(len(payload).to_bytes(4, "big"))
                    audio_request.extend(payload)
                    await ws.send(audio_request)

                    first_chunk = await ws.recv()
                    latency = time.time() - start_time
                    latencies.append(latency)
                    await ws.close()

            except Exception as e:
                print(f"[豆包ASR] 第{i+1}次测试失败: {str(e)}")
                latencies.append(0)

        return self._calculate_result("豆包流式ASR", latencies, test_count)


class QwenASRFlashTester(BaseASRTester):
    def __init__(self):
        super().__init__("Qwen3ASRFlash")

    async def _test_single(self, audio_file_info):
        start_time = time.time()
        temp_file_path = None

        try:
            audio_data = audio_file_info['data']
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file_path = f.name

            with wave.open(temp_file_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_data)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"audio": temp_file_path}
                    ]
                }
            ]

            api_key = self.asr_config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("未配置 api_key")

            if dashscope is None:
                raise RuntimeError("未安装 dashscope 库")

            dashscope.api_key = api_key

            response = dashscope.MultiModalConversation.call(
                model="qwen3-asr-flash",
                messages=messages,
                result_format="message",
                asr_options={"enable_lid": True, "enable_itn": False},
                stream=True
            )

            for chunk in response:
                latency = time.time() - start_time
                return latency

            raise Exception("流式结束，未收到任何响应")

        except Exception as e:
            raise Exception(f"通义ASR流式失败: {str(e)}")

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

    async def test(self, test_count=5):
        if not self.test_audio_files:
            return {"name": "通义千问ASR", "latency": 0, "status": "失败: 未找到测试音频"}
        if not self.asr_config and not os.getenv("DASHSCOPE_API_KEY"):
            return {"name": "通义千问ASR", "latency": 0, "status": "失败: 未配置 api_key"}

        latencies = []
        for i in range(test_count):
            try:
                # print(f"\n[通义ASR] 开始第 {i+1} 次测试...")
                latency = await self._test_single(self.test_audio_files[0])
                latencies.append(latency)
                # print(f"[通义ASR] 第{i+1}次成功 延迟: {latency:.3f}s")
            except Exception as e:
                # print(f"[通义ASR] 第{i+1}次测试失败: {str(e)}")
                latencies.append(0)

        return self._calculate_result("通义千问ASR", latencies, test_count)


class ASRPerformanceSuite:
    def __init__(self):
        self.testers = []
        self.results = []

    def register_tester(self, tester_class):
        try:
            tester = tester_class()
            self.testers.append(tester)
            print(f"已注册测试器: {tester.config_key}")
        except Exception as e:
            name_map = {
                "DoubaoStreamASRTester": "豆包流式ASR",
                "QwenASRFlashTester": "通义千问ASR"
            }
            name = name_map.get(tester_class.__name__, tester_class.__name__)
            print(f"跳过 {name}: {str(e)}")

    def _print_results(self, test_count):
        if not self.results:
            print("没有有效的ASR测试结果")
            return

        print(f"\n{'='*60}")
        print("流式ASR首词响应时间测试结果")
        print(f"{'='*60}")
        print(f"测试次数: 每个ASR服务测试 {test_count} 次")

        success_results = sorted(
            [r for r in self.results if "成功" in r["status"]],
            key=lambda x: x["latency"]
        )
        failed_results = [r for r in self.results if "成功" not in r["status"]]

        table_data = [
            [r["name"], f"{r['latency']:.3f}s" if r['latency'] > 0 else "N/A", r["status"]]
            for r in success_results + failed_results
        ]

        print(tabulate(table_data, headers=["ASR服务", "首词延迟", "状态"], tablefmt="grid"))
        print("\n测试说明：")
        print("- 测量从发送请求到接收第一个有效识别文本的时间")
        print("- 超时控制: DashScope 默认超时，豆包 WebSocket 超时10秒")
        print("- 排序规则: 成功的按延迟升序，失败的排在后面")

    async def run(self, test_count=5):
        print(f"开始流式ASR首词响应时间测试...")
        print(f"每个ASR服务测试次数: {test_count}次\n")

        self.results = []
        for tester in self.testers:
            print(f"\n--- 测试 {tester.config_key} ---")
            result = await tester.test(test_count)
            self.results.append(result)

        self._print_results(test_count)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="流式ASR首词响应时间测试工具")
    parser.add_argument("--count", type=int, default=5, help="测试次数")
    args = parser.parse_args()

    suite = ASRPerformanceSuite()
    suite.register_tester(DoubaoStreamASRTester)
    suite.register_tester(QwenASRFlashTester)

    await suite.run(args.count)


if __name__ == "__main__":
    asyncio.run(main())