import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from config.manage_api_client import report_device_event
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


async def handle_device_event(conn: "ConnectionHandler", msg_json: Dict[str, Any]):
    """处理设备主动上报的事件"""
    event = msg_json.get("event")
    payload = msg_json.get("payload", {})
    timestamp = msg_json.get("timestamp")

    if not event:
        logger.bind(tag=TAG).warning("收到空的 device_event")
        return

    logger.bind(tag=TAG).info(f"设备事件: {event}, payload: {payload}")

    if event == "language_change":
        language = payload.get("language")
        if language:
            await _handle_language_change(conn, language)
    elif event == "beacon_change":
        beacon_id = payload.get("beacon_id")
        if beacon_id:
            await _handle_beacon_change(conn, beacon_id, payload)
    else:
        logger.bind(tag=TAG).debug(f"未识别的设备事件: {event}")

    # 异步上报到 manager-api 持久化
    asyncio.create_task(
        _report_event_to_manager_api(conn, event, payload, timestamp)
    )


async def _handle_language_change(conn: "ConnectionHandler", language: str):
    """处理语言变更事件"""
    conn.device_language = language
    if conn.device_attributes is None:
        conn.device_attributes = {}
    conn.device_attributes["language"] = language
    logger.bind(tag=TAG).info(f"设备语言已切换为: {language}")
    # 重新触发提示词增强，让 LLM 立即感知语言变化
    try:
        conn._init_prompt_enhancement()
    except Exception as e:
        logger.bind(tag=TAG).warning(f"语言切换后刷新提示词失败: {e}")


async def _handle_beacon_change(
    conn: "ConnectionHandler", beacon_id: str, payload: Dict[str, Any]
):
    """处理蓝牙信标变更事件"""
    if conn.device_attributes is None:
        conn.device_attributes = {}
    conn.device_attributes["last_beacon_id"] = beacon_id
    logger.bind(tag=TAG).info(f"设备蓝牙信标已更新: {beacon_id}")


async def _report_event_to_manager_api(
    conn: "ConnectionHandler", event: str, payload: Dict[str, Any], timestamp: Any
):
    """将设备事件上报给 manager-api 持久化"""
    if not conn.read_config_from_api:
        return
    try:
        await report_device_event(
            device_id=conn.device_id,
            event=event,
            payload=payload,
            timestamp=timestamp,
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"上报设备事件失败: {e}")
