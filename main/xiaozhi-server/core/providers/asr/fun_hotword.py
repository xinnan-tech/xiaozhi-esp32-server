import time
import wave
import os
import sys
import io
from config.logger import setup_logging
from typing import Optional, Tuple, List
import uuid
import opuslib_next
from core.providers.asr.base import ASRProviderBase

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
from modelscope.hub.snapshot_download import snapshot_download

TAG = __name__
logger = setup_logging()

# 捕获标准输出
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # 将捕获到的内容通过 logger 输出
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.hotwords_file = config.get("hotwords", "config/assets/hotwords.txt")
        self.model_dir = config.get("model_dir")
        self.vad_dir = config.get("vad_dir")
        self.punc_dir = config.get("punc_dir")
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            logger.bind(tag=TAG).info(f"FunASR_hotword 初始化...")
            # 加载模型
            self.model = self._load_model(model_dir=self.model_dir, vad_dir=self.vad_dir, punc_dir=self.punc_dir)  
            # 读取热词配置
            self.hotwords_str = self._load_hotwords(self.hotwords_file)
            # 逆文本正则化
            self.inverse_normalizer = self._load_itn_model()
            logger.bind(tag=TAG).info(f"FunASR_hotword 初始化完成")

    def _load_model(self, model_dir: str, vad_dir: str, punc_dir: str):
        """加载模型"""
        # 定义模型ID映射
        model_map = {
            "paraformer-zh": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "fsmn-vad": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            "ct-punc-c": "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        }
        # 定义模型目录映射
        model_paths = {
            "paraformer-zh": model_dir,
            "fsmn-vad": vad_dir,
            "ct-punc-c": punc_dir,
        }
        # 下载模型
        for model_name, repo_id in model_map.items():
            model_dir = model_paths[model_name]
            logger.bind(tag=TAG).info(f"加载模型 {model_name}")
            snapshot_download(repo_id, revision="v2.0.4", local_dir=model_dir)
        # 初始化模型
        model = AutoModel(
            model=model_paths["paraformer-zh"],
            vad_model=model_paths["fsmn-vad"],
            punc_model=model_paths["ct-punc-c"],
            vad_kwargs={"max_single_segment_time": 30000},
            disable_update=True,
            hub="ms",
            # device="cuda:0",  # 启用GPU加速
        )
        return model

    def _load_hotwords(self, hotwords_file: str):
        """加载热词"""
        hotwords_str = ""
        if os.path.exists(hotwords_file):
            with open(hotwords_file, encoding="utf-8") as f:
                hotwords_list = []
                hotwords_num = 0
                for line in f.readlines():
                    # 最多读取5000个热词
                    if hotwords_num >= 5000:
                        logger.bind(tag=TAG).warning(f"热词数量超过5000个, 超出部分将被忽略")
                        break

                    line = line.strip()
                    # 跳过空行和注释行
                    if line and not line.startswith("#"):
                        # 格式：word:score 或者 word
                        # 仅提取word部分
                        word = line.split("#")[0].split(":")[0].strip()
                        if len(word.encode("gbk")) > 20: # 用gbk编码计算字节长度 1个中文字符=2个字节
                            logger.bind(tag=TAG).warning(f"热词<{word}>长度超过10个字, 将被忽略")
                            continue
                        hotwords_list.append(word)
                        hotwords_num += 1

                hotwords_str = " ".join(hotwords_list)

                logger.bind(tag=TAG).info(f"已添加{len(hotwords_list)}个热词: {hotwords_str[:100]}{'...' if len(hotwords_str) > 100 else ''}")
        else:
            hotwords_str = hotwords_file

        return hotwords_str

    def _load_itn_model(self):
        """加载逆文本正则化模型"""
        inverse_normalizer = None
        try:
            from itn.chinese.inverse_normalizer import InverseNormalizer
            logger.bind(tag=TAG).info(f"加载逆文本正则化模型...")
            inverse_normalizer = InverseNormalizer()
        except Exception as e:
            logger.bind(tag=TAG).warning(f"逆文本正则化模型加载失败: {e} 请安装WeTextProcessing模块\nWindows: conda install -y -c conda-forge pynini=2.1.5 && pip install WeTextProcessing==1.0.3\nLinux & MacOS: pip install WeTextProcessing")

        return inverse_normalizer

    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """将Opus音频数据解码并保存为WAV文件"""
        file_name = f"asr_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        file_path = None
        try:
            # 保存音频文件
            start_time = time.time()
            file_path = self.save_audio_to_file(opus_data, session_id)
            logger.bind(tag=TAG).debug(f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}")

            # 语音识别
            start_time = time.time()
            result = self.model.generate(
                input=file_path,
                cache={},
                hotword=self.hotwords_str,
                batch_size_s=300,
            )
            # 文本后处理 去除asr标记
            text = rich_transcription_postprocess(result[0]["text"])
            # 逆文本正则化 数字/日期等转为数值化的文本
            text = self.inverse_normalizer.normalize(text) if self.inverse_normalizer else text

            logger.bind(tag=TAG).debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")

            return text, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", None

        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
