"""
安全防护层



功能:
- 白名单验证
- 关键操作用户确认
- 输入输出验证
- 安全日志记录
"""

import re
import time
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Awaitable
from dataclasses import dataclass, field
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"           # 只读操作
    MEDIUM = "medium"     # 普通写操作
    HIGH = "high"         # 敏感操作
    CRITICAL = "critical"  # 关键操作（需用户确认）


class SecurityAction(Enum):
    """安全动作"""
    ALLOW = "allow"       # 允许执行
    DENY = "deny"         # 拒绝执行
    CONFIRM = "confirm"   # 需要确认
    LOG = "log"           # 记录日志


@dataclass
class SecurityEvent:
    """安全事件"""
    tool_name: str
    action: SecurityAction
    level: SecurityLevel
    reason: str
    timestamp: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_confirmed: Optional[bool] = None


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_params: Dict[str, Any] = field(default_factory=dict)


class SecurityGuardrails:
    """
    安全防护层

    提供:
    - 工具白名单验证
    - 关键操作确认机制
    - 参数验证
    - 安全审计
    """

    # ========== 关键操作列表（需用户确认） ==========
    CRITICAL_TOOLS: Set[str] = {
        "order_cancel",      # 取消订单
        "payment_refund",    # 退款
        "account_delete",    # 删除账号
        "password_reset",    # 重置密码
        "data_delete",       # 删除数据
        "config_reset",      # 重置配置
    }

    # ========== 工具白名单 ==========
    TOOL_ALLOWLIST: Set[str] = {
        # 查询类（只读）
        "payment_check", "payment_status",
        "order_search", "order_query", "order_status",
        "user_verify", "user_info",
        "database_query", "api_call",
        "get_weather", "get_time", "get_date",
        "get_news", "get_news_from_chinanews", "get_news_from_newsnow",
        "hass_get_state",
        "search", "query", "get_info",

        # 操作类（需记录）
        "order_create", "order_cancel",
        "payment_refund", "payment_confirm",
        "user_update",
        "hass_set_state", "hass_play_music",
        "play_music", "stop_music", "next_song", "previous_song",
        "change_role",

        # 系统类
        "handle_exit_intent",
        "iot_control",
    }

    # ========== 危险模式 ==========
    DANGEROUS_PATTERNS: List[str] = [
        r"rm\s+-rf",           # 删除命令
        r"DROP\s+TABLE",       # SQL 删除
        r"DELETE\s+FROM",      # SQL 删除
        r"TRUNCATE",           # SQL 清空
        r"exec\s*\(",          # 代码执行
        r"eval\s*\(",          # 代码执行
        r"__import__",         # 动态导入
        r"subprocess",         # 子进程
        r"os\.system",         # 系统命令
    ]

    # ========== 确认话术 ==========
    CONFIRMATION_PROMPTS: Dict[str, str] = {
        "order_cancel": "确认要取消订单吗？请说'确认'或'取消'",
        "payment_refund": "确认要申请退款吗？请说'确认'或'取消'",
        "account_delete": "警告：确认要删除账号吗？此操作不可恢复！请说'确认'或'取消'",
        "password_reset": "确认要重置密码吗？请说'确认'或'取消'",
        "data_delete": "确认要删除数据吗？请说'确认'或'取消'",
        "config_reset": "确认要重置配置吗？请说'确认'或'取消'",
        "default": "确认要执行此操作吗？请说'确认'或'取消'",
    }

    # ========== 确认关键词 ==========
    CONFIRM_WORDS: Set[str] = {"确认", "是的", "对", "好的", "可以", "同意", "确定"}
    CANCEL_WORDS: Set[str] = {"取消", "不", "算了", "不要", "停", "拒绝"}

    def __init__(
        self,
        strict_mode: bool = True,
        enable_logging: bool = True,
        custom_allowlist: Optional[Set[str]] = None,
        on_confirm_request: Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        """
        Args:
            strict_mode: 严格模式（白名单外的工具全部拒绝）
            enable_logging: 启用安全日志
            custom_allowlist: 自定义白名单
            on_confirm_request: 确认请求回调
        """
        self._strict_mode = strict_mode
        self._enable_logging = enable_logging
        self._on_confirm_request = on_confirm_request
        self._event_history: List[SecurityEvent] = []
        self._max_history_size = 1000

        # 合并自定义白名单
        if custom_allowlist:
            self.TOOL_ALLOWLIST = self.TOOL_ALLOWLIST | custom_allowlist

        # 编译危险模式正则
        self._dangerous_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.DANGEROUS_PATTERNS
        ]

    async def validate_and_confirm(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        验证并确认工具执行

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            (是否允许执行, 错误消息)
        """
        start_time = time.time()

        # 1. 白名单验证
        if not self._validate_allowlist(tool_name):
            error = f"工具 {tool_name} 不在白名单中"
            self._record_event(
                tool_name=tool_name,
                action=SecurityAction.DENY,
                level=SecurityLevel.HIGH,
                reason=error,
                parameters=parameters,
            )
            return False, "抱歉，该操作不被允许"

        # 2. 参数验证
        validation = self._validate_parameters(tool_name, parameters)
        if not validation.valid:
            error = "; ".join(validation.errors)
            self._record_event(
                tool_name=tool_name,
                action=SecurityAction.DENY,
                level=SecurityLevel.MEDIUM,
                reason=error,
                parameters=parameters,
            )
            return False, f"参数验证失败: {error}"

        # 3. 关键操作确认
        if self._is_critical_operation(tool_name):
            confirmed = await self._request_confirmation(tool_name, parameters)
            if not confirmed:
                self._record_event(
                    tool_name=tool_name,
                    action=SecurityAction.DENY,
                    level=SecurityLevel.CRITICAL,
                    reason="用户取消操作",
                    parameters=parameters,
                    user_confirmed=False,
                )
                return False, "操作已取消"

            self._record_event(
                tool_name=tool_name,
                action=SecurityAction.ALLOW,
                level=SecurityLevel.CRITICAL,
                reason="用户确认执行",
                parameters=parameters,
                user_confirmed=True,
            )
        else:
            # 记录普通操作
            self._record_event(
                tool_name=tool_name,
                action=SecurityAction.ALLOW,
                level=self._get_security_level(tool_name),
                reason="通过安全验证",
                parameters=parameters,
            )

        logger.bind(tag=TAG).debug(
            f"安全验证通过: {tool_name} "
            f"(耗时 {(time.time() - start_time) * 1000:.1f}ms)"
        )

        return True, None

    def _validate_allowlist(self, tool_name: str) -> bool:
        """验证工具是否在白名单中"""
        # 精确匹配
        if tool_name in self.TOOL_ALLOWLIST:
            return True

        # 动态工具支持（如 IoT 设备）
        if self._is_dynamic_tool(tool_name):
            return True

        # 非严格模式下允许未知工具
        if not self._strict_mode:
            logger.bind(tag=TAG).warning(
                f"工具 {tool_name} 不在白名单中，但非严格模式允许执行"
            )
            return True

        return False

    def _is_dynamic_tool(self, tool_name: str) -> bool:
        """检查是否是动态工具"""
        # IoT 设备工具
        if tool_name.startswith("iot_") or tool_name.startswith("device_"):
            return True
        # MCP 工具
        if tool_name.startswith("mcp_"):
            return True
        return False

    def _validate_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> ValidationResult:
        """验证参数安全性"""
        result = ValidationResult(valid=True, sanitized_params=parameters.copy())

        # 检查危险模式
        for key, value in parameters.items():
            if isinstance(value, str):
                for regex in self._dangerous_regex:
                    if regex.search(value):
                        result.valid = False
                        result.errors.append(
                            f"参数 {key} 包含危险模式: {regex.pattern}"
                        )

        # 检查参数长度
        for key, value in parameters.items():
            if isinstance(value, str) and len(value) > 10000:
                result.warnings.append(f"参数 {key} 过长，可能影响性能")

        return result

    def _is_critical_operation(self, tool_name: str) -> bool:
        """检查是否是关键操作"""
        return tool_name in self.CRITICAL_TOOLS

    async def _request_confirmation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> bool:
        """请求用户确认"""
        prompt = self.CONFIRMATION_PROMPTS.get(
            tool_name,
            self.CONFIRMATION_PROMPTS["default"],
        )

        logger.bind(tag=TAG).info(f"请求用户确认: {tool_name} - {prompt}")

        if self._on_confirm_request:
            try:
                response = await asyncio.wait_for(
                    self._on_confirm_request(prompt),
                    timeout=30.0,
                )
                return self._is_confirmed(response)
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning("用户确认超时")
                return False
            except Exception as e:
                logger.bind(tag=TAG).error(f"确认请求失败: {e}")
                return False

        # 没有确认回调时，默认拒绝
        logger.bind(tag=TAG).warning("无确认回调，默认拒绝关键操作")
        return False

    def _is_confirmed(self, response: str) -> bool:
        """判断用户是否确认"""
        if not response:
            return False

        response_lower = response.strip().lower()

        # 检查确认词
        for word in self.CONFIRM_WORDS:
            if word in response_lower:
                return True

        # 检查取消词
        for word in self.CANCEL_WORDS:
            if word in response_lower:
                return False

        # 默认拒绝（安全优先）
        return False

    def _get_security_level(self, tool_name: str) -> SecurityLevel:
        """获取工具安全级别"""
        if tool_name in self.CRITICAL_TOOLS:
            return SecurityLevel.CRITICAL

        # 写操作
        write_keywords = ["create", "update", "delete", "set", "cancel", "reset"]
        for keyword in write_keywords:
            if keyword in tool_name.lower():
                return SecurityLevel.MEDIUM

        # 默认为低风险（只读）
        return SecurityLevel.LOW

    def _record_event(
        self,
        tool_name: str,
        action: SecurityAction,
        level: SecurityLevel,
        reason: str,
        parameters: Dict[str, Any],
        user_confirmed: Optional[bool] = None,
    ) -> None:
        """记录安全事件"""
        event = SecurityEvent(
            tool_name=tool_name,
            action=action,
            level=level,
            reason=reason,
            timestamp=time.time(),
            parameters=self._sanitize_params_for_log(parameters),
            user_confirmed=user_confirmed,
        )

        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]

        if self._enable_logging:
            log_func = logger.bind(tag=TAG).info
            if action == SecurityAction.DENY:
                log_func = logger.bind(tag=TAG).warning
            log_func(
                f"安全事件: {action.value} {tool_name} "
                f"(level={level.value}, reason={reason})"
            )

    def _sanitize_params_for_log(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """清理参数用于日志记录（脱敏）"""
        sensitive_keys = {"password", "token", "secret", "key", "auth"}
        result = {}

        for key, value in parameters.items():
            if any(s in key.lower() for s in sensitive_keys):
                result[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 100:
                result[key] = value[:100] + "..."
            else:
                result[key] = value

        return result

    def add_to_allowlist(self, tool_name: str) -> None:
        """添加工具到白名单"""
        self.TOOL_ALLOWLIST.add(tool_name)
        logger.bind(tag=TAG).info(f"已添加工具到白名单: {tool_name}")

    def remove_from_allowlist(self, tool_name: str) -> None:
        """从白名单移除工具"""
        self.TOOL_ALLOWLIST.discard(tool_name)
        logger.bind(tag=TAG).info(f"已从白名单移除工具: {tool_name}")

    def add_critical_tool(self, tool_name: str) -> None:
        """添加关键操作工具"""
        self.CRITICAL_TOOLS.add(tool_name)
        logger.bind(tag=TAG).info(f"已添加关键操作工具: {tool_name}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        action_counts = {}
        level_counts = {}

        for event in self._event_history:
            action_counts[event.action.value] = (
                action_counts.get(event.action.value, 0) + 1
            )
            level_counts[event.level.value] = (
                level_counts.get(event.level.value, 0) + 1
            )

        return {
            "total_events": len(self._event_history),
            "by_action": action_counts,
            "by_level": level_counts,
            "allowlist_size": len(self.TOOL_ALLOWLIST),
            "critical_tools": len(self.CRITICAL_TOOLS),
        }

    def get_recent_events(self, count: int = 20) -> List[Dict[str, Any]]:
        """获取最近的安全事件"""
        recent = self._event_history[-count:]
        return [
            {
                "tool_name": e.tool_name,
                "action": e.action.value,
                "level": e.level.value,
                "reason": e.reason,
                "timestamp": e.timestamp,
                "user_confirmed": e.user_confirmed,
            }
            for e in recent
        ]

    def get_denied_tools(self) -> List[str]:
        """获取被拒绝的工具列表"""
        denied = set()
        for event in self._event_history:
            if event.action == SecurityAction.DENY:
                denied.add(event.tool_name)
        return list(denied)

