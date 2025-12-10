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
import hmac
import base64
import hashlib
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
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
        """计算测试结果（修复：正确处理None值，剔除失败测试）"""
        # 剔除None值（失败的测试）和无效延迟，只统计有效延迟
        valid_latencies = [l for l in latencies if l is not None and l > 0]
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

    def _generate_header(
        self,
        version=0x01,
        message_type=0x01,
        message_type_specific_flags=0x00,
        serial_method=0x01,
        compression_type=0x01,
        reserved_data=0x00,
        extension_header: bytes = b"",
    ):
        """生成协议头（修复：使用正确的Header格式）"""
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header

    def _generate_audio_default_header(self):
        """生成音频数据Header"""
        return self._generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x00,  # 普通音频帧
            serial_method=0x01,
            compression_type=0x01,
        )

    def _generate_last_audio_header(self):
        """生成最后一帧音频的Header（标记音频结束）"""
        return self._generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x02,  # 0x02表示这是最后一帧
            serial_method=0x01,
            compression_type=0x01,
        )

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
                cluster = self.asr_config.get("cluster", "volcengine_input_common")
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
                        "app": {"appid": appid, "cluster": cluster, "token": access_token},
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

                    # 发送音频数据（使用最后一帧标记，告诉服务端音频已结束）
                    payload = gzip.compress(audio_data)
                    audio_request = bytearray(self._generate_last_audio_header())  # 修复：使用最后一帧Header
                    audio_request.extend(len(payload).to_bytes(4, "big"))
                    audio_request.extend(payload)
                    await ws.send(audio_request)

                    first_chunk = await ws.recv()
                    latency = time.time() - start_time
                    latencies.append(latency)
                    print(f"[豆包ASR] 第{i+1}次 首词延迟: {latency:.3f}s")
                    await ws.close()

            except Exception as e:
                print(f"[豆包ASR] 第{i+1}次测试失败: {str(e)}")
                latencies.append(None)

        return self._calculate_result("豆包流式ASR", latencies, test_count)


class QwenASRFlashTester(BaseASRTester):
    def __init__(self):
        super().__init__("Qwen3ASRFlash")

    async def _test_single(self, audio_file_info):
        temp_file_path = None

        try:
            audio_data = audio_file_info['data']

            # 优化：将临时文件准备工作移到计时前，减少磁盘IO对性能测试的影响
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

            # 统一计时起点：在API调用前开始计时（但文件准备已完成）
            start_time = time.time()

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
                print(f"[通义ASR] 第{i+1}次 首词延迟: {latency:.3f}s")
            except Exception as e:
                # print(f"[通义ASR] 第{i+1}次测试失败: {str(e)}")
                latencies.append(None)

        return self._calculate_result("通义千问ASR", latencies, test_count)


class XunfeiStreamASRTester(BaseASRTester):
    def __init__(self):
        super().__init__("XunfeiStreamASR")

    def _create_url(self):
        url = "wss://iat-api.xfyun.cn/v2/iat"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: iat-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1"
        signature_sha = hmac.new(
            self.asr_config["api_secret"].encode('utf-8'),
            signature_origin.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode()

        authorization_origin = f'api_key="{self.asr_config["api_key"]}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode()).decode()

        v = {"authorization": authorization, "date": date, "host": "iat-api.xfyun.cn"}
        return url + "?" + parse.urlencode(v)

    async def test(self, test_count: int = 5):
        if not self.test_audio_files:
            return {"name": "讯飞流式ASR", "latency": 0, "status": "失败: 未找到测试音频"}
        if not self.asr_config:
            return {"name": "讯飞流式ASR", "latency": 0, "status": "失败: 未配置"}

        required = ["app_id", "api_key", "api_secret"]
        for k in required:
            if k not in self.asr_config:
                return {"name": "讯飞流式ASR", "latency": 0, "status": f"失败: 缺少配置 {k}"}

        latencies = []
        frame_size = 1280
        audio_raw = self.test_audio_files[0]['data']
        if audio_raw.startswith(b'RIFF'):
            audio_raw = audio_raw[44:]

        for i in range(test_count):
            try:
                start_time = time.time()
                ws_url = self._create_url()

                async with websockets.connect(
                    ws_url,
                    additional_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    max_size=1 << 30,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=30,
                ) as ws:

                    # 第一帧：移除 punc 字段，避免未知参数错误
                    await ws.send(json.dumps({
                        "common": {"app_id": self.asr_config["app_id"]},
                        "business": {
                            "domain": "iat",
                            "language": "zh_cn",
                            "accent": "mandarin",
                            "dwa": "wpgs",
                            "vad_eos": 5000
                            # 已移除 "punc": True
                        },
                        "data": {
                            "status": 0,
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw",
                            "audio": base64.b64encode(audio_raw[:frame_size]).decode()
                        }
                    }, ensure_ascii=False))

                    # 后续所有帧
                    pos = frame_size
                    while pos < len(audio_raw):
                        chunk = audio_raw[pos:pos + frame_size]
                        status = 2 if (pos + frame_size >= len(audio_raw)) else 1
                        await ws.send(json.dumps({
                            "data": {
                                "status": status,
                                "format": "audio/L16;rate=16000",
                                "encoding": "raw",
                                "audio": base64.b64encode(chunk).decode()
                            }
                        }, ensure_ascii=False))
                        if status == 2:
                            break
                        pos += frame_size

                    # 接收首词
                    first_token = True
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("code") != 0:
                            raise Exception(f"讯飞错误: {data.get('message')}")

                        ws_result = data.get("data", {}).get("result", {}).get("ws")
                        if ws_result:
                            text = "".join(cw.get("w", "") for seg in ws_result for cw in seg.get("cw", []))
                            if text.strip() and first_token:
                                latency = time.time() - start_time
                                latencies.append(latency)
                                print(f"[讯飞ASR] 第{i+1}次 首词延迟: {latency:.3f}s")
                                first_token = False
                                break

            except Exception as e:
                print(f"[讯飞ASR] 第{i+1}次测试失败: {str(e)}")
                latencies.append(None)

        return self._calculate_result("讯飞流式ASR", latencies, test_count)
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
                "QwenASRFlashTester": "通义千问ASR",
                "XunfeiStreamASRTester": "讯飞流式ASR"
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
        print("- 计时起点: 建立连接前（包含握手、发送音频、接收首个识别结果全流程）")
        print("- 通义千问优化: 临时文件准备在计时前完成，减少磁盘IO对测试的影响")
        print("- 错误处理: 失败的测试不计入平均值，只统计成功测试的延迟")
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
    suite.register_tester(XunfeiStreamASRTester)

    await suite.run(args.count)


if __name__ == "__main__":
    asyncio.run(main())