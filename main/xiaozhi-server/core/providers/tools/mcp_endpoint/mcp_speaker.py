"""把已识别的说话人附到 MCP 接入点 tools/call 上。

工具参数保持模型给出的原样。身份放在 MCP 的 params._meta 里，
接入点上的服务可以读取，不读的服务按协议忽略。
"""

from typing import Any, Dict, Optional

from core.utils.voiceprint_provider import UNKNOWN_SPEAKER_NAME


def should_forward_speaker(config: Optional[dict]) -> bool:
    """mcp_forward_speaker 缺省为开启。显式 false 时不附带身份。"""
    if not isinstance(config, dict):
        return True
    return bool(config.get("mcp_forward_speaker", True))


def speaker_call_meta(speaker_id: Any, speaker_name: Any) -> Optional[Dict[str, str]]:
    """有真实身份时返回 _meta；没有则返回 None，调用方不写这个字段。"""
    meta: Dict[str, str] = {}
    if isinstance(speaker_id, str):
        speaker_id = speaker_id.strip()
        if speaker_id:
            meta["speakerId"] = speaker_id
    if isinstance(speaker_name, str):
        speaker_name = speaker_name.strip()
        if speaker_name and speaker_name != UNKNOWN_SPEAKER_NAME:
            meta["speakerName"] = speaker_name
    return meta or None


def build_mcp_endpoint_tool_payload(
    tool_call_id: int,
    name: str,
    arguments: Dict[str, Any],
    meta: Optional[Dict[str, str]] = None,
) -> dict:
    """组装 tools/call。meta 为空时不出现 _meta，参数字典原样放进 arguments。"""
    params: Dict[str, Any] = {"name": name, "arguments": arguments}
    if meta:
        params["_meta"] = meta
    return {
        "jsonrpc": "2.0",
        "id": tool_call_id,
        "method": "tools/call",
        "params": params,
    }
