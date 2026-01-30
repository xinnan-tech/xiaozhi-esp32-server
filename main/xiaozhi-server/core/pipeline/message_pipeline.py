from abc import ABC, abstractmethod
from typing import Any, List


class MessageProcessor(ABC):
    """消息处理器接口。返回 True 表示已处理并中止后续处理。"""

    @abstractmethod
    async def process(self, context: Any, transport: Any, message: Any) -> bool:
        raise NotImplementedError


class MessagePipeline:
    """责任链式消息处理管道。"""

    def __init__(self) -> None:
        self._processors: List[MessageProcessor] = []

    def add_processor(self, processor: MessageProcessor) -> None:
        self._processors.append(processor)

    async def process_message(self, context: Any, transport: Any, message: Any) -> None:
        for processor in self._processors:
            handled = await processor.process(context, transport, message)
            if handled:
                return


