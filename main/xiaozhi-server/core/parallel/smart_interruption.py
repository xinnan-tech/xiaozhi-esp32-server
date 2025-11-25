"""
智能打断整合模块

将 InterruptionHandler 与现有 VAD 打断机制整合。

原有流程:
    VAD检测声音 → 立即打断（不考虑意图）

新流程:
    VAD检测声音 → ASR识别 → 意图分析 → 决定是否打断
    - 明确打断词（等等、停）→ 打断
    - 隐式打断词（我想问）→ 打断并准备新查询
    - 反馈信号（嗯、好的）→ 不打断，继续播放
"""

import time
import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .interruption_handler import (
    InterruptionHandler,
    InterruptionType,
    InterruptionConfig,
)
from .feature_flags import FeatureFlag, get_feature_manager


class InterruptionDecision(Enum):
    """打断决策"""
    INTERRUPT = "interrupt"           # 打断
    CONTINUE = "continue"             # 继续播放（反馈信号）
    DEFER = "defer"                   # 延迟决策（等待 ASR）


@dataclass
class SmartInterruptionConfig:
    """智能打断配置"""
    enabled: bool = True
    # VAD 层面配置
    vad_interrupt_enabled: bool = True      # 是否启用 VAD 立即打断
    vad_interrupt_in_manual_mode: bool = False  # manual 模式下是否打断
    # 意图层面配置
    intent_interrupt_enabled: bool = True   # 是否启用意图打断
    skip_backchannel: bool = True           # 是否跳过反馈信号
    # 响应时间目标
    target_response_ms: float = 400.0


class SmartInterruptionManager:
    """
    智能打断管理器

    整合 VAD 打断和意图打断两种机制。
    """

    def __init__(
        self,
        config: Optional[SmartInterruptionConfig] = None,
        logger: Any = None,
    ):
        self.config = config or SmartInterruptionConfig()
        self.logger = logger
        self._feature_manager = get_feature_manager()

        # 初始化 InterruptionHandler
        self._interruption_handler = InterruptionHandler(
            config=InterruptionConfig(
                enabled=self.config.intent_interrupt_enabled,
                target_response_ms=self.config.target_response_ms,
            )
        )

        # 统计
        self._vad_interrupts = 0
        self._intent_interrupts = 0
        self._skipped_backchannels = 0

    def is_smart_interruption_enabled(self) -> bool:
        """检查智能打断是否启用"""
        return (
            self.config.enabled
            and self._feature_manager.is_enabled(FeatureFlag.SMART_INTERRUPTION)
        )

    def should_interrupt_on_vad(
        self,
        have_voice: bool,
        is_speaking: bool,
        listen_mode: str,
    ) -> InterruptionDecision:
        """
        VAD 层面决策：是否应该打断

        Args:
            have_voice: VAD 检测到声音
            is_speaking: 服务端是否正在说话
            listen_mode: 监听模式 (auto/manual/realtime)

        Returns:
            InterruptionDecision
        """
        # 没有声音或没在说话，不需要打断
        if not have_voice or not is_speaking:
            return InterruptionDecision.CONTINUE

        # manual 模式不打断
        if listen_mode == "manual" and not self.config.vad_interrupt_in_manual_mode:
            return InterruptionDecision.CONTINUE

        # 如果启用智能打断，延迟到意图分析再决定
        if self.is_smart_interruption_enabled():
            return InterruptionDecision.DEFER

        # 传统模式：VAD 检测到声音就打断
        if self.config.vad_interrupt_enabled:
            self._vad_interrupts += 1
            return InterruptionDecision.INTERRUPT

        return InterruptionDecision.CONTINUE

    async def should_interrupt_on_text(
        self,
        text: str,
        is_speaking: bool,
        listen_mode: str,
    ) -> tuple[InterruptionDecision, Optional[InterruptionType]]:
        """
        文本层面决策：根据 ASR 识别结果决定是否打断

        Args:
            text: ASR 识别的文本
            is_speaking: 服务端是否正在说话
            listen_mode: 监听模式

        Returns:
            (InterruptionDecision, InterruptionType)
        """
        # 不在说话，不需要打断
        if not is_speaking:
            return InterruptionDecision.CONTINUE, None

        # manual 模式不打断
        if listen_mode == "manual":
            return InterruptionDecision.CONTINUE, None

        # 检测打断意图
        interruption_type = self._interruption_handler._detect_interruption(text)

        if not interruption_type:
            # 没有检测到打断意图，但有文字输入，按传统逻辑打断
            self._vad_interrupts += 1
            return InterruptionDecision.INTERRUPT, None

        # 反馈信号：不打断
        if interruption_type == InterruptionType.BACKCHANNEL:
            if self.config.skip_backchannel:
                self._skipped_backchannels += 1
                if self.logger:
                    self.logger.info(f"跳过反馈信号: {text}")
                return InterruptionDecision.CONTINUE, interruption_type
            else:
                # 配置为不跳过反馈信号
                self._intent_interrupts += 1
                return InterruptionDecision.INTERRUPT, interruption_type

        # 明确/隐式打断：打断
        self._intent_interrupts += 1
        if self.logger:
            self.logger.info(f"意图打断: {interruption_type.value} - {text}")
        return InterruptionDecision.INTERRUPT, interruption_type

    async def handle_interruption(
        self,
        text: str,
        is_speaking: bool,
        listen_mode: str,
        abort_callback: Optional[Callable[[], Any]] = None,
        immediate_response_callback: Optional[Callable[[str], Any]] = None,
    ) -> bool:
        """
        完整的打断处理流程

        Args:
            text: ASR 识别的文本
            is_speaking: 服务端是否正在说话
            listen_mode: 监听模式
            abort_callback: 打断回调（清空队列、停止 TTS）
            immediate_response_callback: 即时响应回调（如播放"好的，您说"）

        Returns:
            bool: 是否执行了打断
        """
        start_time = time.time()

        decision, int_type = await self.should_interrupt_on_text(
            text, is_speaking, listen_mode
        )

        if decision != InterruptionDecision.INTERRUPT:
            return False

        # 执行打断
        if abort_callback:
            try:
                result = abort_callback()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self.logger:
                    self.logger.error(f"打断回调失败: {e}")

        # 即时响应
        if immediate_response_callback and int_type in [
            InterruptionType.EXPLICIT,
            InterruptionType.IMPLICIT,
        ]:
            response = self._get_interruption_response(int_type)
            if response:
                try:
                    result = immediate_response_callback(response)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"即时响应回调失败: {e}")

        elapsed_ms = (time.time() - start_time) * 1000
        if self.logger:
            self.logger.info(f"打断处理完成: {elapsed_ms:.1f}ms")

        return True

    def _get_interruption_response(
        self,
        interruption_type: InterruptionType,
    ) -> str:
        """获取打断响应话术"""
        responses = {
            InterruptionType.EXPLICIT: "好的，您说",
            InterruptionType.IMPLICIT: "好的，我听着",
            InterruptionType.BACKCHANNEL: "",
        }
        return responses.get(interruption_type, "")

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "enabled": self.is_smart_interruption_enabled(),
            "vad_interrupts": self._vad_interrupts,
            "intent_interrupts": self._intent_interrupts,
            "skipped_backchannels": self._skipped_backchannels,
            "handler_stats": self._interruption_handler.get_statistics(),
        }

    def reset_statistics(self) -> None:
        """重置统计"""
        self._vad_interrupts = 0
        self._intent_interrupts = 0
        self._skipped_backchannels = 0


# ============== 整合函数 ==============

async def smart_interrupt_check(
    conn,
    text: str,
) -> bool:
    """
    智能打断检查（供 startToChat 调用）

    Args:
        conn: ConnectionHandler 实例
        text: ASR 识别的文本

    Returns:
        bool: 是否应该继续处理（False 表示跳过，如反馈信号）
    """
    # 检查特性开关
    feature_manager = get_feature_manager()
    if not feature_manager.is_enabled(FeatureFlag.SMART_INTERRUPTION):
        return True  # 未启用智能打断，继续正常处理

    # 获取或创建管理器
    if not hasattr(conn, '_smart_interruption_manager'):
        conn._smart_interruption_manager = SmartInterruptionManager(
            logger=conn.logger if hasattr(conn, 'logger') else None,
        )

    manager = conn._smart_interruption_manager

    # 检测是否是反馈信号
    decision, int_type = await manager.should_interrupt_on_text(
        text=text,
        is_speaking=getattr(conn, 'client_is_speaking', False),
        listen_mode=getattr(conn, 'client_listen_mode', 'auto'),
    )

    # 反馈信号：不处理，直接返回
    if int_type == InterruptionType.BACKCHANNEL and decision == InterruptionDecision.CONTINUE:
        return False

    return True


def should_skip_vad_interrupt(
    conn,
    have_voice: bool,
) -> bool:
    """
    是否应该跳过 VAD 立即打断（供 handleAudioMessage 调用）

    智能打断模式下，VAD 检测到声音不立即打断，
    而是等待 ASR 识别完成后再决定。

    Args:
        conn: ConnectionHandler 实例
        have_voice: VAD 是否检测到声音

    Returns:
        bool: True=跳过立即打断，False=执行传统打断
    """
    # 检查特性开关
    feature_manager = get_feature_manager()
    if not feature_manager.is_enabled(FeatureFlag.SMART_INTERRUPTION):
        return False  # 未启用智能打断，使用传统逻辑

    # 智能打断模式：跳过 VAD 立即打断
    return True


