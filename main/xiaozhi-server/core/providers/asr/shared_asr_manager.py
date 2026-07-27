"""
SharedASRManager: 全局 ASR 管理器
实现单例模型 + 单推理执行器 + 队列限流。
单例的原因是：推理是 CPU/GPU-bound，不是 I/O-bound，多实例不仅会占用内存，还会降低吞吐能力
"""

import asyncio
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Tuple, List
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__


class SharedASRManager:
    """
    全局共享 ASR 管理器
    """

    # 支持预加载的本地模型类型
    LOCAL_MODEL_TYPES = [
        "fun_local",           # FunASR 本地
        "sherpa_onnx_local",   # Sherpa ONNX
        "sense_voice"          # SenseVoice
    ]

    def __init__(self, config: Dict[str, Any], asr_type: str = None):
        """
        初始化 ASR 管理器
        Args:
            config: 服务器配置
            asr_type: ASR 类型（Optional，用于显式指定）
        """
        self.config = config
        self.asr_type = asr_type

        # 模型实例（全局单例）
        self.model_instance = None

        # 任务队列（限流）
        queue_max_size = self._get_queue_max_size()
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max_size)

        # 推理锁（使得推理串行化）
        self.inference_lock = asyncio.Lock()
        # 线程池执行器，用于阻塞调用
        self.executor: Optional[ThreadPoolExecutor] = None

        # 运行状态
        self.running = False
        self._inference_task: Optional[asyncio.Task] = None
        self.is_local_model = self._check_local_model()
        self._variant_lock = asyncio.Lock()
        self._variant_managers = {}
        self._max_shared_models = max(
            1, int(config.get("shared_asr_max_models", 3) or 3)
        )

        logger.bind(tag=TAG).info(
            f"SharedASRManager 初始化完成, "
            f"类型: {self.asr_type}, "
            f"本地模型: {self.is_local_model}, "
            f"队列大小: {queue_max_size}"
        )

    def _get_queue_max_size(self) -> int:
        """获取队列最大大小"""
        # 尝试从配置获取
        selected_asr = self.config.get("selected_module", {}).get("ASR")
        if selected_asr:
            asr_config = self.config.get("ASR", {}).get(selected_asr, {})
            return asr_config.get("queue_max_size", 100)
        return 100

    def _check_local_model(self) -> bool:
        """检查是否为本地模型"""
        if self.asr_type:
            return self.asr_type in self.LOCAL_MODEL_TYPES

        # 从配置推断
        selected_asr = self.config.get("selected_module", {}).get("ASR")
        if not selected_asr:
            return False

        asr_config = self.config.get("ASR", {}).get(selected_asr, {})
        asr_type = asr_config.get("type", selected_asr)
        self.asr_type = asr_type

        return asr_type in self.LOCAL_MODEL_TYPES

    async def initialize(self):
        """
        初始化管理器
        - 预加载模型
        - 启动推理执行器
        """
        if not self.is_local_model:
            logger.bind(tag=TAG).info("非本地模型，跳过预加载")
            return

        if self.running:
            logger.bind(tag=TAG).warning("管理器已在运行中")
            return

        try:
            logger.bind(tag=TAG).info(f"开始预加载 ASR 模型: {self.asr_type}")

            # 预加载模型
            await self._preload_model()

            # 启动推理执行器
            self.running = True
            self._inference_task = asyncio.create_task(self._inference_loop())

            logger.bind(tag=TAG).info("ASR 模型预加载完成，推理执行器已启动")

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR 模型预加载失败: {e}")
            raise

    async def _preload_model(self):
        """在线程池中预加载模型"""
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="asr_worker")

        loop = asyncio.get_event_loop()
        self.model_instance = await loop.run_in_executor(
            self.executor,
            self._create_model_instance
        )

        logger.bind(tag=TAG).info("模型实例创建完成")

    def _create_model_instance(self):
        """
        实际创建模型实例（在线程中执行）

        Returns:
            ASR Provider 实例
        """
        from core.utils.modules_initialize import initialize_asr

        logger.bind(tag=TAG).info("正在创建 ASR 模型实例...")
        instance = initialize_asr(self.config)
        logger.bind(tag=TAG).info("ASR 模型实例创建成功")

        return instance

    async def submit_task(
        self,
        opus_data: List[bytes],
        session_id: str,
        audio_format: str = "opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        提交推理任务

        Args:
            opus_data: 音频数据
            session_id: 会话 ID
            audio_format: 音频格式

        Returns:
            (识别文本, 文件路径)

        Raises:
            RuntimeError: 队列满或服务未运行
        """
        if not self.running:
            raise RuntimeError("ASR 服务未运行")

        # 检查队列是否满（限流）
        if self.task_queue.full():
            queue_status = self.get_queue_status()
            logger.bind(tag=TAG).warning(
                f"ASR 队列已满: {queue_status}"
            )
            raise RuntimeError("ASR 服务繁忙，请稍后重试")

        # 创建 Future 用于返回结果
        result_future: asyncio.Future = asyncio.Future()

        # 构造任务
        task = {
            'opus_data': opus_data,
            'session_id': session_id,
            'audio_format': audio_format,
            'future': result_future
        }

        # 放入队列
        await self.task_queue.put(task)

        logger.bind(tag=TAG).debug(
            f"任务已提交, session: {session_id}, "
            f"队列大小: {self.task_queue.qsize()}"
        )

        # 等待结果
        return await result_future

    async def _inference_loop(self):
        """
        单个推理执行器循环

        核心原则：
        - 只有一个执行器
        - 串行处理任务
        - 带超时的队列获取
        """
        logger.bind(tag=TAG).info("推理执行器启动")

        while self.running:
            task = None
            try:
                # 带超时的队列获取，避免关闭时卡住
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # 超时后检查 running 状态，继续循环
                    continue

                if task['future'].done():
                    continue

                # 执行推理（加锁保证串行）
                async with self.inference_lock:
                    if task['future'].done():
                        continue
                    result = await self._run_inference(
                        task['opus_data'],
                        task['session_id'],
                        task['audio_format']
                    )

                # 返回结果
                if not task['future'].done():
                    task['future'].set_result(result)

                logger.bind(tag=TAG).debug(
                    f"推理完成, session: {task['session_id']}"
                )

            except asyncio.CancelledError:
                logger.bind(tag=TAG).info("推理执行器被取消")
                break
            except Exception as e:
                logger.bind(tag=TAG).error(f"推理执行失败: {e}")
                if task and 'future' in task and not task['future'].done():
                    task['future'].set_exception(e)
            finally:
                if task is not None:
                    self.task_queue.task_done()

        logger.bind(tag=TAG).info("推理执行器已停止")

    async def _run_inference(
        self,
        opus_data: List[bytes],
        session_id: str,
        audio_format: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        执行实际推理（在线程池中）

        Args:
            opus_data: 音频数据
            session_id: 会话 ID
            audio_format: 音频格式

        Returns:
            (识别文本, 文件路径)
        """
        loop = asyncio.get_event_loop()

        # 在线程池中执行推理
        result = await loop.run_in_executor(
            self.executor,
            lambda: self._sync_wrapper(opus_data, session_id)
        )

        return result

    def _sync_wrapper(
        self,
        opus_data: List[bytes],
        session_id: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Run the provider's complete artifact wrapper in the worker thread."""
        import asyncio

        async def _call():
            return await self.model_instance.speech_to_text_wrapper(
                opus_data, session_id
            )

        # 创建新的事件循环执行
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_call())
            return result
        finally:
            if loop:
                loop.close()

    def matches_config(self, config: Dict[str, Any]) -> bool:
        """Return whether this manager owns the exact selected ASR config."""
        selected = config.get("selected_module", {}).get("ASR")
        manager_selected = self.config.get("selected_module", {}).get("ASR")
        if not selected or selected != manager_selected:
            return False
        return (
            config.get("ASR", {}).get(selected)
            == self.config.get("ASR", {}).get(manager_selected)
            and bool(config.get("delete_audio", True))
            == bool(self.config.get("delete_audio", True))
        )

    @classmethod
    def _config_fingerprint(cls, config: Dict[str, Any]) -> str:
        selected = config.get("selected_module", {}).get("ASR")
        payload = {
            "selected": selected,
            "config": config.get("ASR", {}).get(selected),
            "delete_audio": bool(config.get("delete_audio", True)),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _config_is_local(cls, config: Dict[str, Any]) -> bool:
        selected = config.get("selected_module", {}).get("ASR")
        asr_config = config.get("ASR", {}).get(selected, {})
        asr_type = asr_config.get("type", selected)
        return asr_type in cls.LOCAL_MODEL_TYPES

    async def acquire_for_config(
        self, config: Dict[str, Any]
    ) -> Optional["SharedASRManager"]:
        """Acquire a bounded shared local model matching one Agent config."""
        if self.matches_config(config):
            return self if self.is_ready() else None
        if not self._config_is_local(config):
            return None

        fingerprint = self._config_fingerprint(config)
        async with self._variant_lock:
            entry = self._variant_managers.get(fingerprint)
            if entry is not None:
                entry["references"] += 1
                return entry["manager"]

            if len(self._variant_managers) >= self._max_shared_models - 1:
                idle_fingerprint = next(
                    (
                        key
                        for key, candidate in self._variant_managers.items()
                        if candidate["references"] == 0
                    ),
                    None,
                )
                if idle_fingerprint is None:
                    raise RuntimeError(
                        "ASR共享模型容量已满，请提高shared_asr_max_models或统一Agent ASR配置"
                    )
                idle_manager = self._variant_managers.pop(
                    idle_fingerprint
                )["manager"]
                # Keep the lock until shutdown completes so a replacement can
                # never overlap the retiring model and exceed the hard limit.
                await idle_manager.shutdown()

            manager = SharedASRManager(copy.deepcopy(config))
            try:
                await manager.initialize()
            except Exception:
                await manager.shutdown()
                raise
            self._variant_managers[fingerprint] = {
                "manager": manager,
                "references": 1,
            }
            logger.bind(tag=TAG).info(
                "已加载Agent专用共享ASR模型，当前模型数: {}",
                len(self._variant_managers) + 1,
            )
            return manager

    async def release_for_config(self, manager: "SharedASRManager") -> None:
        """Release an Agent model; idle variants stay cached for safe reuse."""
        if manager is self:
            return
        async with self._variant_lock:
            for entry in self._variant_managers.values():
                if entry["manager"] is not manager:
                    continue
                entry["references"] = max(0, entry["references"] - 1)
                break

    async def shutdown(self):
        """
        优雅停机

        步骤：
        1. 停止接收新任务
        2. 等待当前任务完成（带超时）
        3. 取消未完成的任务
        4. 关闭线程池
        """
        async with self._variant_lock:
            variants = [
                entry["manager"] for entry in self._variant_managers.values()
            ]
            self._variant_managers.clear()
        if variants:
            await asyncio.gather(
                *(manager.shutdown() for manager in variants),
                return_exceptions=True,
            )

        if (
            not self.running
            and self.executor is None
            and self.model_instance is None
        ):
            return

        logger.bind(tag=TAG).info("开始关闭 ASR 管理器...")

        # 停止接收新任务
        self.running = False

        # 等待推理任务完成
        if self._inference_task and not self._inference_task.done():
            try:
                # 最多等待 5 秒
                await asyncio.wait_for(
                    self._inference_task,
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning("推理任务超时，强制取消")
                self._inference_task.cancel()
                try:
                    await self._inference_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass

        # 取消所有队列中未完成的任务
        cancelled_count = 0
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                if not task['future'].done():
                    task['future'].set_exception(
                        RuntimeError("ASR 服务正在关闭")
                    )
                    cancelled_count += 1
            except asyncio.QueueEmpty:
                break

        if cancelled_count > 0:
            logger.bind(tag=TAG).info(f"已取消 {cancelled_count} 个待处理任务")

        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None
            logger.bind(tag=TAG).info("线程池已关闭")

        # 清理模型实例
        self.model_instance = None

        logger.bind(tag=TAG).info("ASR 管理器已关闭")

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态（用于监控）

        Returns:
            队列状态字典
        """
        queue_size = self.task_queue.qsize()
        queue_max = self.task_queue.maxsize

        return {
            'queue_size': queue_size,
            'queue_max': queue_max,
            'is_busy': queue_size > queue_max * 0.8,
            'utilization': queue_size / queue_max if queue_max > 0 else 0,
            'running': self.running
        }

    def is_ready(self) -> bool:
        """检查管理器是否就绪"""
        return (
            self.running and
            self.model_instance is not None and
            self.executor is not None
        )

    @classmethod
    def is_local_model_type(cls, asr_type: str) -> bool:
        """
        检查 ASR 类型是否为本地模型

        Args:
            asr_type: ASR 类型

        Returns:
            是否为本地模型
        """
        return asr_type in cls.LOCAL_MODEL_TYPES
