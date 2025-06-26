"""
Opus编码工具类
将PCM音频数据编码为Opus格式
"""

import logging
import traceback

import numpy as np
from typing import List, Optional
from opuslib_next import Encoder
from opuslib_next import constants


class OpusEncoderUtils:
    """PCM到Opus的编码器"""

    def __init__(self, sample_rate: int, channels: int, frame_size_ms: int):
        """
        初始化Opus编码器

        Args:
            sample_rate: 采样率 (Hz)
            channels: 通道数 (1=单声道, 2=立体声)
            frame_size_ms: 帧大小 (毫秒)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size_ms = frame_size_ms
        # 计算每帧样本数 = 采样率 * 帧大小(毫秒) / 1000
        self.frame_size = (sample_rate * frame_size_ms) // 1000
        # 总帧大小 = 每帧样本数 * 通道数
        self.total_frame_size = self.frame_size * channels

        # 比特率和复杂度设置
        self.bitrate = 24000  # bps
        self.complexity = 10  # 最高质量

        # 缓冲区初始化为空
        self.buffer = np.array([], dtype=np.int16)

        try:
            # 创建Opus编码器
            self.encoder = Encoder(
                sample_rate, channels, constants.APPLICATION_AUDIO  # 音频优化模式
            )
            self.encoder.bitrate = self.bitrate
            self.encoder.complexity = self.complexity
            self.encoder.signal = constants.SIGNAL_VOICE  # 语音信号优化
        except Exception as e:
            logging.error(f"初始化Opus编码器失败: {e}")
            raise RuntimeError("初始化失败") from e

    def reset_state(self):
        """重置编码器状态"""
        self.encoder.reset_state()
        self.buffer = np.array([], dtype=np.int16)

    def encode_pcm_to_opus(self, pcm_data: bytes, end_of_stream: bool) -> List[bytes]:
        """
        将PCM数据编码为Opus格式

        Args:
            pcm_data: PCM字节数据
            end_of_stream: 是否为流的结束

        Returns:
            Opus数据包列表
        """
        # 将字节数据转换为short数组
        new_samples = self._convert_bytes_to_shorts(pcm_data)

        # 校验PCM数据
        self._validate_pcm_data(new_samples)

        # 将新数据追加到缓冲区
        self.buffer = np.append(self.buffer, new_samples)

        opus_packets = []
        offset = 0

        # 处理所有完整帧
        while offset <= len(self.buffer) - self.total_frame_size:
            frame = self.buffer[offset : offset + self.total_frame_size]
            output = self._encode(frame)
            if output:
                opus_packets.append(output)
            offset += self.total_frame_size

        # 保留未处理的样本
        self.buffer = self.buffer[offset:]

        # 流结束时处理剩余数据
        if end_of_stream and len(self.buffer) > 0:
            # 创建最后一帧并用0填充
            last_frame = np.zeros(self.total_frame_size, dtype=np.int16)
            last_frame[: len(self.buffer)] = self.buffer

            output = self._encode(last_frame)
            if output:
                opus_packets.append(output)
            self.buffer = np.array([], dtype=np.int16)

        return opus_packets

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        """编码一帧音频数据"""
        try:
            # 将numpy数组转换为bytes
            frame_bytes = frame.tobytes()
            # opuslib要求输入字节数必须是channels*2的倍数
            encoded = self.encoder.encode(frame_bytes, self.frame_size)
            return encoded
        except Exception as e:
            logging.error(f"Opus编码失败: {e}")
            traceback.print_exc()
            return None

    def _convert_bytes_to_shorts(self, bytes_data: bytes) -> np.ndarray:
        """将字节数组转换为short数组 (16位PCM)"""
        # 假设输入是小端字节序的16位PCM
        return np.frombuffer(bytes_data, dtype=np.int16)

    def _validate_pcm_data(self, pcm_shorts: np.ndarray) -> None:
        """验证PCM数据是否有效"""
        # 16位PCM数据范围是 -32768 到 32767
        if np.any((pcm_shorts < -32768) | (pcm_shorts > 32767)):
            invalid_samples = pcm_shorts[(pcm_shorts < -32768) | (pcm_shorts > 32767)]
            logging.warning(f"发现无效PCM样本: {invalid_samples[:5]}...")
            # 在实际应用中可以选择裁剪而不是抛出异常
            # np.clip(pcm_shorts, -32768, 32767, out=pcm_shorts)

    def close(self):
        """关闭编码器并释放资源"""
        # opuslib没有明确的关闭方法，Python的垃圾回收会处理
        pass
