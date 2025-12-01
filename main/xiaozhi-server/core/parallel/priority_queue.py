"""
TTS 优先级队列

避免消息乱序，支持:
- 打断消息（最高优先级）
- 过渡响应（次高优先级）
- 最终响应（正常优先级）
"""

import heapq
import threading
import time
import uuid
from enum import IntEnum
from typing import Optional, Any, List, Tuple
from dataclasses import dataclass, field
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class PriorityLevel(IntEnum):
    """优先级级别（数值越小优先级越高）"""
    INTERRUPT = 0       # 打断消息（最高优先级）
    TRANSITION = 1      # 过渡响应
    BACKCHANNEL = 2     # 反馈信号
    NORMAL = 3          # 正常响应
    LOW = 4             # 低优先级


@dataclass(order=True)
class PriorityItem:
    """
    优先级队列项

    排序规则:
    1. priority: 优先级（越小越先）
    2. sequence_num: 序列号（越小越先）
    3. timestamp: 时间戳（越小越先）
    """
    priority: int
    sequence_num: int
    timestamp: float = field(compare=True)
    sentence_id: str = field(compare=False)
    content: Any = field(compare=False)
    metadata: dict = field(default_factory=dict, compare=False)


class TTSPriorityQueue:
    """
    TTS 优先级队列

    特性:
    - 线程安全
    - 优先级排序
    - 序列号保证顺序
    - 支持超时获取
    - 统计功能
    """

    def __init__(self, maxsize: int = 0):
        """
        Args:
            maxsize: 最大队列大小，0表示无限制
        """
        self._heap: List[PriorityItem] = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._maxsize = maxsize
        self._sequence_counter = 0
        self._total_put = 0
        self._total_get = 0

    def put(
        self,
        content: Any,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        sentence_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        放入队列

        Args:
            content: 内容
            priority: 优先级
            sentence_id: 句子ID
            metadata: 附加元数据
            block: 是否阻塞
            timeout: 超时时间

        Returns:
            bool: 是否成功
        """
        with self._not_full:
            if self._maxsize > 0:
                if not block:
                    if len(self._heap) >= self._maxsize:
                        return False
                elif timeout is None:
                    while len(self._heap) >= self._maxsize:
                        self._not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    end_time = time.time() + timeout
                    while len(self._heap) >= self._maxsize:
                        remaining = end_time - time.time()
                        if remaining <= 0.0:
                            return False
                        self._not_full.wait(remaining)

            item = PriorityItem(
                priority=priority.value,
                sequence_num=self._sequence_counter,
                timestamp=time.time(),
                sentence_id=sentence_id or str(uuid.uuid4().hex),
                content=content,
                metadata=metadata or {},
            )
            heapq.heappush(self._heap, item)
            self._sequence_counter += 1
            self._total_put += 1
            self._not_empty.notify()
            return True

    def get(
        self,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> Optional[PriorityItem]:
        """
        从队列获取

        Args:
            block: 是否阻塞
            timeout: 超时时间

        Returns:
            PriorityItem or None
        """
        with self._not_empty:
            if not block:
                if not self._heap:
                    return None
            elif timeout is None:
                while not self._heap:
                    self._not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                end_time = time.time() + timeout
                while not self._heap:
                    remaining = end_time - time.time()
                    if remaining <= 0.0:
                        return None
                    self._not_empty.wait(remaining)

            item = heapq.heappop(self._heap)
            self._total_get += 1
            self._not_full.notify()
            return item

    def get_nowait(self) -> Optional[PriorityItem]:
        """非阻塞获取"""
        return self.get(block=False)

    def put_nowait(
        self,
        content: Any,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        sentence_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """非阻塞放入"""
        return self.put(
            content=content,
            priority=priority,
            sentence_id=sentence_id,
            metadata=metadata,
            block=False,
        )

    def peek(self) -> Optional[PriorityItem]:
        """查看队首元素（不移除）"""
        with self._lock:
            return self._heap[0] if self._heap else None

    def clear(self) -> int:
        """
        清空队列

        Returns:
            int: 清除的元素数量
        """
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
            self._not_full.notify_all()
            logger.bind(tag=TAG).debug(f"队列已清空，移除 {count} 个元素")
            return count

    def clear_by_priority(self, priority: PriorityLevel) -> int:
        """
        清除指定优先级及更低优先级的元素

        Args:
            priority: 优先级阈值

        Returns:
            int: 清除的元素数量
        """
        with self._lock:
            original_count = len(self._heap)
            self._heap = [
                item for item in self._heap
                if item.priority < priority.value
            ]
            heapq.heapify(self._heap)
            removed = original_count - len(self._heap)
            self._not_full.notify_all()
            return removed

    def qsize(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._heap)

    def empty(self) -> bool:
        """检查队列是否为空"""
        with self._lock:
            return len(self._heap) == 0

    def full(self) -> bool:
        """检查队列是否已满"""
        with self._lock:
            return self._maxsize > 0 and len(self._heap) >= self._maxsize

    def get_statistics(self) -> dict:
        """获取队列统计信息"""
        with self._lock:
            priority_counts = {}
            for item in self._heap:
                level = PriorityLevel(item.priority).name
                priority_counts[level] = priority_counts.get(level, 0) + 1

            return {
                "current_size": len(self._heap),
                "maxsize": self._maxsize,
                "total_put": self._total_put,
                "total_get": self._total_get,
                "priority_distribution": priority_counts,
            }

    def get_items_by_sentence(self, sentence_id: str) -> List[PriorityItem]:
        """获取指定句子的所有元素"""
        with self._lock:
            return [
                item for item in self._heap
                if item.sentence_id == sentence_id
            ]

    def remove_by_sentence(self, sentence_id: str) -> int:
        """移除指定句子的所有元素"""
        with self._lock:
            original_count = len(self._heap)
            self._heap = [
                item for item in self._heap
                if item.sentence_id != sentence_id
            ]
            heapq.heapify(self._heap)
            removed = original_count - len(self._heap)
            self._not_full.notify_all()
            return removed


class TTSMessageQueue:
    """
    TTS 消息队列封装

    提供更高级的接口，兼容原有的 queue.Queue 接口
    """

    def __init__(self, maxsize: int = 0):
        self._priority_queue = TTSPriorityQueue(maxsize)

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """放入队列（兼容 queue.Queue 接口）"""
        # 从 item 中提取优先级信息
        priority = PriorityLevel.NORMAL
        sentence_id = None

        if hasattr(item, 'priority'):
            priority = PriorityLevel(item.priority)
        if hasattr(item, 'sentence_id'):
            sentence_id = item.sentence_id

        self._priority_queue.put(
            content=item,
            priority=priority,
            sentence_id=sentence_id,
            block=block,
            timeout=timeout,
        )

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取（兼容 queue.Queue 接口）"""
        item = self._priority_queue.get(block=block, timeout=timeout)
        if item:
            return item.content
        raise Empty()

    def get_nowait(self) -> Any:
        """非阻塞获取"""
        item = self._priority_queue.get_nowait()
        if item:
            return item.content
        raise Empty()

    def put_nowait(self, item: Any) -> None:
        """非阻塞放入"""
        success = self._priority_queue.put_nowait(content=item)
        if not success:
            raise Full()

    def qsize(self) -> int:
        """获取队列大小"""
        return self._priority_queue.qsize()

    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._priority_queue.empty()

    def full(self) -> bool:
        """检查队列是否已满"""
        return self._priority_queue.full()

    def task_done(self) -> None:
        """标记任务完成（兼容接口，此处为空实现）"""
        pass

    def clear(self) -> int:
        """清空队列"""
        return self._priority_queue.clear()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self._priority_queue.get_statistics()


class Empty(Exception):
    """队列为空异常"""
    pass


class Full(Exception):
    """队列已满异常"""
    pass





