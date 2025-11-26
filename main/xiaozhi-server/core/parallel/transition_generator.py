"""
过渡响应生成器

在工具执行前给用户即时反馈，提升用户体验。

三级策略:
- Level 1: 规则映射（<50ms）→ 覆盖 70% 场景
- Level 2: 模板引擎（<80ms）→ 覆盖 20% 场景
- Level 3: LLM 生成（200ms）→ 覆盖 10% 场景
"""

import re
import time
import random
from enum import Enum
from typing import Dict, Optional, List, Tuple, Any, Callable
from dataclasses import dataclass, field
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ResponseLevel(Enum):
    """响应生成级别"""
    RULE = "rule"           # 规则映射
    TEMPLATE = "template"   # 模板引擎
    LLM = "llm"             # LLM 生成


@dataclass
class TransitionResponse:
    """过渡响应"""
    text: str
    level: ResponseLevel
    tool_name: str
    generation_time_ms: float
    confidence: float = 1.0


@dataclass
class ToolCategory:
    """工具类别"""
    name: str
    keywords: List[str]
    default_response: str
    templates: List[str] = field(default_factory=list)


class TransitionResponseGenerator:
    """
    过渡响应生成器

    目标：
    - Level 1 响应延迟 < 50ms
    - 规则匹配覆盖率 > 70%
    - 过渡响应准确率 > 95%
    """

    # ========== Level 1: 规则映射表 ==========
    TOOL_RESPONSE_MAP: Dict[str, str] = {
        # ==================== 医疗场景 ====================
        # 患者信息
        "patient_query": "正在查询患者信息",
        "patient_search": "正在搜索患者档案",
        "patient_info": "正在获取患者资料",
        "patient_history": "正在调取病史记录",

        # 病历相关
        "medical_record": "正在查询病历",
        "medical_record_query": "正在调取病历记录",
        "medical_record_create": "正在创建病历",
        "medical_record_update": "正在更新病历信息",
        "diagnosis_query": "正在查询诊断记录",
        "diagnosis_history": "正在调取诊断历史",

        # 检查报告
        "report_query": "正在查询检查报告",
        "lab_result": "正在获取化验结果",
        "imaging_report": "正在调取影像报告",
        "test_result": "正在查询检测结果",

        # 处方药品
        "prescription_query": "正在查询处方信息",
        "prescription_create": "正在开具处方",
        "medication_query": "正在查询用药记录",
        "drug_interaction": "正在检查药物相互作用",

        # 预约挂号
        "appointment_query": "正在查询预约信息",
        "appointment_create": "正在预约挂号",
        "appointment_cancel": "正在取消预约",
        "schedule_query": "正在查询排班信息",

        # 医疗建议
        "symptom_analysis": "正在分析症状",
        "treatment_suggestion": "正在生成治疗建议",
        "follow_up_reminder": "正在设置随访提醒",

        # ==================== 会议场景 ====================
        # 会议管理
        "meeting_query": "正在查询会议信息",
        "meeting_create": "正在创建会议",
        "meeting_update": "正在更新会议安排",
        "meeting_cancel": "正在取消会议",
        "meeting_schedule": "正在安排会议时间",

        # 会议记录
        "meeting_summary": "正在生成会议纪要",
        "meeting_minutes": "正在整理会议记录",
        "transcript_query": "正在查询转写记录",
        "action_items": "正在提取行动事项",
        "key_points": "正在提炼关键要点",

        # 参会人员
        "attendee_query": "正在查询参会人员",
        "attendee_invite": "正在发送会议邀请",
        "attendee_confirm": "正在确认参会状态",

        # 日程管理
        "calendar_query": "正在查询日程安排",
        "calendar_add": "正在添加日程",
        "calendar_update": "正在更新日程",
        "availability_check": "正在检查时间空闲",

        # 任务跟进
        "task_create": "正在创建任务",
        "task_assign": "正在分配任务",
        "task_query": "正在查询任务状态",
        "task_update": "正在更新任务进度",
        "deadline_reminder": "正在设置截止提醒",

        # ==================== 销售场景 ====================
        # 客户管理
        "customer_query": "正在查询客户信息",
        "customer_search": "正在搜索客户档案",
        "customer_create": "正在创建客户资料",
        "customer_update": "正在更新客户信息",
        "customer_history": "正在调取客户往来记录",

        # 销售机会
        "opportunity_query": "正在查询销售机会",
        "opportunity_create": "正在创建商机",
        "opportunity_update": "正在更新商机状态",
        "pipeline_query": "正在查询销售管道",
        "lead_query": "正在查询潜在客户",

        # 报价合同
        "quote_create": "正在生成报价单",
        "quote_query": "正在查询报价信息",
        "contract_query": "正在查询合同状态",
        "contract_create": "正在创建合同",
        "price_query": "正在查询价格信息",

        # 订单跟进
        "order_search": "正在查找订单记录",
        "order_query": "正在查询订单信息",
        "order_cancel": "正在取消订单",
        "order_status": "正在查询订单状态",
        "order_create": "正在创建订单",
        "order_follow_up": "正在查询订单跟进情况",

        # 业绩统计
        "sales_report": "正在生成销售报告",
        "performance_query": "正在查询业绩数据",
        "target_query": "正在查询销售目标",
        "commission_query": "正在计算佣金",

        # 拜访记录
        "visit_record": "正在记录拜访信息",
        "visit_query": "正在查询拜访记录",
        "visit_plan": "正在规划拜访计划",

        # ==================== 通用场景 ====================
        # 支付相关
        "payment_check": "正在查询支付情况",
        "payment_status": "正在查询支付状态",
        "payment_refund": "正在处理退款申请",
        "payment_confirm": "正在确认支付信息",

        # 用户相关
        "user_verify": "正在验证身份信息",
        "user_info": "正在获取用户信息",
        "user_update": "正在更新用户资料",
        "password_reset": "正在处理密码重置",

        # 查询类
        "database_query": "正在查询数据",
        "api_call": "正在获取信息",
        "search": "正在搜索",
        "get_info": "正在获取信息",
        "query": "正在查询",

        # 天气时间
        "get_weather": "正在查询天气",
        "get_time": "正在查询时间",
        "get_date": "正在查询日期",

        # 新闻资讯
        "get_news": "正在获取最新资讯",
        "get_news_from_chinanews": "正在获取中国新闻",
        "get_news_from_newsnow": "正在获取最新新闻",

        # 智能家居
        "hass_get_state": "正在查询设备状态",
        "hass_set_state": "正在控制设备",
        "hass_play_music": "正在播放音乐",
        "iot_control": "正在控制设备",

        # 音乐播放
        "play_music": "正在播放音乐",
        "stop_music": "正在停止播放",
        "next_song": "切换下一首",
        "previous_song": "切换上一首",

        # 系统操作
        "change_role": "正在切换角色",
        "handle_exit_intent": "好的，再见",

        # 通用
        "default": "请稍等，正在处理",
    }

    # ========== Level 2: 工具类别定义 ==========
    TOOL_CATEGORIES: List[ToolCategory] = [
        # ==================== 核心场景 ====================
        ToolCategory(
            name="medical",
            keywords=[
                "patient", "medical", "diagnosis", "prescription", "病历",
                "患者", "诊断", "处方", "检查", "报告", "symptom", "treatment",
                "lab", "imaging", "medication", "drug", "病史", "随访",
            ],
            default_response="正在处理医疗信息",
            templates=[
                "正在{action}{target}",
                "正在调取{target}记录",
                "正在处理{target}信息",
            ],
        ),
        ToolCategory(
            name="meeting",
            keywords=[
                "meeting", "calendar", "schedule", "attendee", "会议",
                "日程", "参会", "纪要", "transcript", "minutes", "agenda",
                "invite", "availability", "录音", "转写", "要点",
            ],
            default_response="正在处理会议相关信息",
            templates=[
                "正在{action}会议{target}",
                "正在整理{target}",
                "正在处理{target}",
            ],
        ),
        ToolCategory(
            name="sales",
            keywords=[
                "customer", "client", "opportunity", "quote", "contract",
                "客户", "商机", "报价", "合同", "销售", "pipeline", "lead",
                "commission", "performance", "visit", "拜访", "业绩",
            ],
            default_response="正在处理销售信息",
            templates=[
                "正在{action}客户{target}",
                "正在处理{target}信息",
                "正在{action}{target}",
            ],
        ),
        ToolCategory(
            name="task",
            keywords=[
                "task", "todo", "action", "assign", "deadline", "任务",
                "待办", "跟进", "提醒", "follow", "reminder",
            ],
            default_response="正在处理任务信息",
            templates=[
                "正在{action}任务",
                "正在处理{target}",
            ],
        ),
        # ==================== 通用场景 ====================
        ToolCategory(
            name="payment",
            keywords=["payment", "pay", "支付", "付款", "refund", "退款"],
            default_response="正在处理支付相关请求",
            templates=[
                "正在{action}支付{target}",
                "正在处理{target}信息",
            ],
        ),
        ToolCategory(
            name="order",
            keywords=["order", "订单", "购买", "购物"],
            default_response="正在处理订单",
            templates=[
                "正在{action}订单",
                "正在{action}订单信息",
            ],
        ),
        ToolCategory(
            name="query",
            keywords=["query", "search", "get", "fetch", "查询", "搜索", "获取"],
            default_response="正在查询信息",
            templates=[
                "正在{action}{target}",
                "正在查询{target}",
            ],
        ),
        ToolCategory(
            name="user",
            keywords=["user", "account", "用户", "账户", "profile", "资料"],
            default_response="正在处理账户信息",
            templates=[
                "正在{action}账户{target}",
                "正在处理{target}信息",
            ],
        ),
        ToolCategory(
            name="iot",
            keywords=["hass", "iot", "device", "智能", "设备", "home"],
            default_response="正在控制设备",
            templates=[
                "正在{action}{target}",
                "正在{action}设备",
            ],
        ),
        ToolCategory(
            name="media",
            keywords=["music", "play", "音乐", "播放", "song", "video"],
            default_response="正在处理媒体请求",
            templates=[
                "正在{action}",
                "正在{action}媒体",
            ],
        ),
    ]

    # ========== 动作词映射 ==========
    ACTION_MAP: Dict[str, str] = {
        # 通用动作
        "check": "查询",
        "query": "查询",
        "get": "获取",
        "search": "搜索",
        "create": "创建",
        "update": "更新",
        "delete": "删除",
        "cancel": "取消",
        "confirm": "确认",
        "verify": "验证",
        "set": "设置",
        "play": "播放",
        "stop": "停止",
        "add": "添加",
        "remove": "移除",
        "list": "列出",
        "show": "显示",
        # 医疗场景
        "diagnose": "诊断",
        "prescribe": "开具",
        "examine": "检查",
        "analyze": "分析",
        "record": "记录",
        "review": "审查",
        # 会议场景
        "schedule": "安排",
        "invite": "邀请",
        "summarize": "总结",
        "transcribe": "转写",
        "extract": "提取",
        "assign": "分配",
        # 销售场景
        "follow": "跟进",
        "quote": "报价",
        "close": "成交",
        "visit": "拜访",
        "track": "追踪",
        "convert": "转化",
    }

    def __init__(
        self,
        llm_generator: Optional[Callable[[str, str], str]] = None,
        enable_llm_fallback: bool = False,
    ):
        """
        Args:
            llm_generator: LLM 生成函数 (tool_name, query) -> response
            enable_llm_fallback: 是否启用 LLM 回退
        """
        self._llm_generator = llm_generator
        self._enable_llm_fallback = enable_llm_fallback
        self._cache: Dict[str, TransitionResponse] = {}
        self._max_cache_size = 500

        # 统计信息
        self._stats = {
            ResponseLevel.RULE: 0,
            ResponseLevel.TEMPLATE: 0,
            ResponseLevel.LLM: 0,
        }

    def generate(
        self,
        tool_name: str,
        query: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> TransitionResponse:
        """
        生成过渡响应

        Args:
            tool_name: 工具名称
            query: 用户查询（可选）
            arguments: 工具参数（可选）

        Returns:
            TransitionResponse
        """
        start_time = time.time()

        # 检查缓存
        cache_key = self._build_cache_key(tool_name, arguments)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.bind(tag=TAG).debug(
                f"命中缓存: {tool_name} -> {cached.text}"
            )
            return cached

        # Level 1: 规则映射
        response = self._try_rule_mapping(tool_name)
        if response:
            self._record_response(response, cache_key, start_time)
            return response

        # Level 2: 模板引擎
        response = self._try_template_engine(tool_name, arguments)
        if response:
            self._record_response(response, cache_key, start_time)
            return response

        # Level 3: LLM 生成
        if self._enable_llm_fallback and self._llm_generator:
            response = self._try_llm_generation(tool_name, query)
            if response:
                self._record_response(response, cache_key, start_time)
                return response

        # 兜底响应
        return self._create_fallback_response(tool_name, start_time)

    def _try_rule_mapping(
        self,
        tool_name: str,
    ) -> Optional[TransitionResponse]:
        """Level 1: 规则映射"""
        start = time.time()

        # 精确匹配
        if tool_name in self.TOOL_RESPONSE_MAP:
            text = self.TOOL_RESPONSE_MAP[tool_name]
            return TransitionResponse(
                text=text,
                level=ResponseLevel.RULE,
                tool_name=tool_name,
                generation_time_ms=(time.time() - start) * 1000,
                confidence=1.0,
            )

        # 模糊匹配（包含关系）
        for key, text in self.TOOL_RESPONSE_MAP.items():
            if key in tool_name or tool_name in key:
                return TransitionResponse(
                    text=text,
                    level=ResponseLevel.RULE,
                    tool_name=tool_name,
                    generation_time_ms=(time.time() - start) * 1000,
                    confidence=0.8,
                )

        return None

    def _try_template_engine(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Optional[TransitionResponse]:
        """Level 2: 模板引擎"""
        start = time.time()

        # 查找匹配的类别
        category = self._find_category(tool_name)
        if not category:
            return None

        # 解析动作和目标
        action = self._extract_action(tool_name)
        target = self._extract_target(tool_name, arguments)

        # 选择模板
        if category.templates:
            template = random.choice(category.templates)
            text = template.format(action=action, target=target)
        else:
            text = category.default_response

        return TransitionResponse(
            text=text,
            level=ResponseLevel.TEMPLATE,
            tool_name=tool_name,
            generation_time_ms=(time.time() - start) * 1000,
            confidence=0.7,
        )

    def _try_llm_generation(
        self,
        tool_name: str,
        query: Optional[str],
    ) -> Optional[TransitionResponse]:
        """Level 3: LLM 生成"""
        if not self._llm_generator:
            return None

        start = time.time()
        try:
            text = self._llm_generator(tool_name, query or "")
            if text:
                return TransitionResponse(
                    text=text,
                    level=ResponseLevel.LLM,
                    tool_name=tool_name,
                    generation_time_ms=(time.time() - start) * 1000,
                    confidence=0.9,
                )
        except Exception as e:
            logger.bind(tag=TAG).error(f"LLM 生成失败: {e}")

        return None

    def _create_fallback_response(
        self,
        tool_name: str,
        start_time: float,
    ) -> TransitionResponse:
        """创建兜底响应"""
        text = self.TOOL_RESPONSE_MAP.get("default", "请稍等")
        return TransitionResponse(
            text=text,
            level=ResponseLevel.RULE,
            tool_name=tool_name,
            generation_time_ms=(time.time() - start_time) * 1000,
            confidence=0.5,
        )

    def _find_category(self, tool_name: str) -> Optional[ToolCategory]:
        """查找工具类别"""
        tool_lower = tool_name.lower()
        for category in self.TOOL_CATEGORIES:
            for keyword in category.keywords:
                if keyword in tool_lower:
                    return category
        return None

    def _extract_action(self, tool_name: str) -> str:
        """从工具名提取动作"""
        parts = re.split(r"[_\-]", tool_name.lower())
        for part in parts:
            if part in self.ACTION_MAP:
                return self.ACTION_MAP[part]
        return "处理"

    def _extract_target(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> str:
        """从工具名和参数提取目标"""
        # 从参数中提取
        if arguments:
            for key in ["name", "target", "item", "query"]:
                if key in arguments and arguments[key]:
                    return str(arguments[key])[:20]

        # 从工具名提取
        parts = re.split(r"[_\-]", tool_name.lower())
        for part in parts:
            if part not in self.ACTION_MAP and len(part) > 2:
                return part

        return "信息"

    def _build_cache_key(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建缓存键"""
        if arguments:
            # 只使用部分参数构建键
            key_args = {k: v for k, v in arguments.items() if k in ["type", "category"]}
            return f"{tool_name}:{hash(frozenset(key_args.items()))}"
        return tool_name

    def _record_response(
        self,
        response: TransitionResponse,
        cache_key: str,
        start_time: float,
    ) -> None:
        """记录响应"""
        response.generation_time_ms = (time.time() - start_time) * 1000

        # 更新缓存
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = response

        # 更新统计
        self._stats[response.level] += 1

        logger.bind(tag=TAG).debug(
            f"过渡响应: {response.tool_name} -> {response.text} "
            f"({response.level.value}, {response.generation_time_ms:.1f}ms)"
        )

    def add_custom_mapping(self, tool_name: str, response: str) -> None:
        """添加自定义映射"""
        self.TOOL_RESPONSE_MAP[tool_name] = response
        logger.bind(tag=TAG).info(f"添加自定义映射: {tool_name} -> {response}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = sum(self._stats.values())
        return {
            "total_generations": total,
            "by_level": {level.value: count for level, count in self._stats.items()},
            "rule_coverage": (
                self._stats[ResponseLevel.RULE] / total
                if total > 0
                else 0
            ),
            "cache_size": len(self._cache),
            "cache_hit_rate": 0,  # TODO: 实现缓存命中率统计
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.bind(tag=TAG).info("过渡响应缓存已清空")


