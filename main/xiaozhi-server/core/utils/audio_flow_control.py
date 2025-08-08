"""
音频流控模块
包含令牌桶算法和音频流控制器的实现
"""

import asyncio
import time
import threading
from collections import deque
from typing import Optional, Dict, Any


class TokenBucket:
    """令牌桶实现，用于限流控制"""

    def __init__(self, capacity: int, refill_rate: float, initial_tokens: Optional[int] = None):
        """
        初始化令牌桶

        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 令牌补充速率（每秒补充的令牌数）
            initial_tokens: 初始令牌数，默认为桶容量
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill_time = time.time()
        self.lock = threading.Lock()

    def get_tokens(self, requested_tokens: int = 1) -> bool:
        """
        获取指定数量的令牌

        Args:
            requested_tokens: 请求的令牌数量

        Returns:
            bool: 是否成功获取到令牌
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= requested_tokens:
                self.tokens -= requested_tokens
                return True
            else:
                return False

    def get_available_tokens(self) -> int:
        """获取当前可用令牌数"""
        with self.lock:
            self._refill_tokens()
            return int(self.tokens)

    def _refill_tokens(self):
        """内部方法：补充令牌"""
        current_time = time.time()
        time_passed = current_time - self.last_refill_time
        tokens_to_add = time_passed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill_time = current_time


class AudioFlowController:
    """音频流控制器，基于令牌桶算法控制音频数据发送"""

    def __init__(self, max_device_buffer: int = 3000, refill_rate: float = 20):
        """
        初始化音频流控制器

        Args:
            max_device_buffer: 设备端最大缓冲区大小（Opus帧数）
            refill_rate: 令牌补充速率（每秒允许发送的帧数）
        """
        self.max_device_buffer = max_device_buffer
        self.token_bucket = TokenBucket(
            capacity=max_device_buffer,
            refill_rate=refill_rate,
            initial_tokens=max_device_buffer // 2  # 初始令牌为容量的一半
        )
        self.sent_frames_count = 0  # 已发送帧数计数
        self.device_consumed_frames = 0  # 设备端已消费帧数
        self.pending_queue = deque()  # 等待发送的数据队列
        self._lock = threading.Lock()

    def can_send_frames(self, frame_count: int) -> bool:
        """
        检查是否可以发送指定数量的帧

        Args:
            frame_count: 要发送的帧数

        Returns:
            bool: 是否可以发送
        """
        with self._lock:
            # 检查设备端缓冲区是否会溢出
            estimated_device_buffer = self.sent_frames_count - self.device_consumed_frames
            if estimated_device_buffer + frame_count > self.max_device_buffer:
                return False

            # 检查令牌桶是否有足够令牌
            return self.token_bucket.get_tokens(frame_count)

    def update_device_consumption(self, consumed_frames: int):
        """
        更新设备端消费的帧数

        Args:
            consumed_frames: 设备端消费的帧数
        """
        with self._lock:
            self.device_consumed_frames += consumed_frames

    def record_sent_frames(self, frame_count: int):
        """
        记录已发送的帧数

        Args:
            frame_count: 发送的帧数
        """
        with self._lock:
            self.sent_frames_count += frame_count

    def get_status(self) -> Dict[str, Any]:
        """获取流控状态信息"""
        with self._lock:
            estimated_buffer = self.sent_frames_count - self.device_consumed_frames
            return {
                "sent_frames": self.sent_frames_count,
                "consumed_frames": self.device_consumed_frames,
                "estimated_device_buffer": estimated_buffer,
                "available_tokens": self.token_bucket.get_available_tokens(),
                "pending_queue_size": len(self.pending_queue),
                "buffer_usage_percent": (estimated_buffer / self.max_device_buffer) * 100
            }

    def reset(self):
        """重置流控状态"""
        with self._lock:
            self.sent_frames_count = 0
            self.device_consumed_frames = 0
            self.pending_queue.clear()
            # 重新初始化令牌桶
            self.token_bucket = TokenBucket(
                capacity=self.max_device_buffer,
                refill_rate=self.token_bucket.refill_rate,
                initial_tokens=self.max_device_buffer // 2
            )


async def simulate_device_consumption(flow_controller: AudioFlowController, frame_count: int):
    """
    模拟设备消费音频帧的过程
    实际应用中应该根据设备反馈来更新消费情况

    Args:
        flow_controller: 流控制器实例
        frame_count: 消费的帧数
    """
    # 模拟设备播放延迟（60ms per frame）
    await asyncio.sleep(frame_count * 0.06)
    flow_controller.update_device_consumption(frame_count)


# 流控配置常量
class FlowControlConfig:
    """流控配置常量"""
    # Opus 编码参数
    OPUS_FRAME_DURATION_MS = 60  # Opus帧时长（毫秒）
    OPUS_FRAMES_PER_SECOND = 1000 / OPUS_FRAME_DURATION_MS  # 每秒帧数

    # 默认流控参数
    DEFAULT_MAX_DEVICE_BUFFER = 40  # 设备端最大缓冲帧数
    DEFAULT_REFILL_RATE = OPUS_FRAMES_PER_SECOND  # 默认令牌补充速率（帧/秒）
    DEFAULT_MAX_WAIT_TIME = 5.0  # 流控最大等待时间（秒）
    DEFAULT_RETRY_INTERVAL = 0.06  # 流控重试间隔（秒）

    # 预缓冲参数
    PRE_BUFFER_FRAMES = 3  # 预缓冲帧数

    @classmethod
    def create_flow_controller(cls, max_buffer: Optional[int] = None,
                               refill_rate: Optional[float] = None) -> AudioFlowController:
        """
        创建流控制器的工厂方法

        Args:
            max_buffer: 最大缓冲区大小，使用默认值如果为None
            refill_rate: 令牌补充速率，使用默认值如果为None

        Returns:
            AudioFlowController: 配置好的流控制器实例
        """
        return AudioFlowController(
            max_device_buffer=max_buffer or cls.DEFAULT_MAX_DEVICE_BUFFER,
            refill_rate=refill_rate or cls.DEFAULT_REFILL_RATE
        )