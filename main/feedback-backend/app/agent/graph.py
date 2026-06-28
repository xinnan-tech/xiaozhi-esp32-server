"""轻量 Agent Graph。

不是完整 LangGraph 依赖，而是一个小型有向执行器：
Intent -> Plan -> Execute skills -> Summarize。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class AgentStep:
    skill: str
    args: dict = field(default_factory=dict)
    risk: str = "read"
    result: Any = None
    error: Optional[str] = None


@dataclass
class AgentState:
    message: str
    store_id: Optional[str] = None
    operator: str = ""
    intent: str = "unknown"
    steps: list[AgentStep] = field(default_factory=list)
    final_answer: str = ""
    route: Optional[str] = None
    data: Any = None
    trace: list[dict] = field(default_factory=list)


class AgentGraph:
    def __init__(self, planner: Callable[[AgentState], AgentState], executor: Callable[[AgentState, AgentStep], Any], summarizer: Callable[[AgentState], AgentState]):
        self.planner = planner
        self.executor = executor
        self.summarizer = summarizer

    async def run(self, state: AgentState) -> AgentState:
        state = self.planner(state)
        for step in state.steps:
            try:
                step.result = await self.executor(state, step)
                state.trace.append({"skill": step.skill, "risk": step.risk, "ok": True})
            except Exception as exc:  # MVP：失败即停止
                step.error = str(exc)
                state.trace.append({"skill": step.skill, "risk": step.risk, "ok": False, "error": step.error})
                break
        return self.summarizer(state)
