import asyncio
from typing import Any, Dict, Tuple

from config.logger import setup_logging
from core.utils.modules_initialize import initialize_modules
from core.providers.asr.shared_asr_manager import SharedASRManager


def _validate_selected_modules(config: Dict[str, Any]) -> Tuple[bool, str]:
    selected = config.get("selected_module", {})
    required_sections = {
        "VAD": "VAD",
        "ASR": "ASR",
        "LLM": "LLM",
        "TTS": "TTS",
        "Memory": "Memory",
        "Intent": "Intent",
    }
    for module_key, section_key in required_sections.items():
        module_name = selected.get(module_key)
        if not module_name:
            continue
        section = config.get(section_key, {})
        if module_name not in section:
            return False, f"{section_key}配置缺失: {module_name}"
    return True, ""


async def _cleanup_instance(instance: Any) -> None:
    if instance is None:
        return
    try:
        if hasattr(instance, "close"):
            result = instance.close()
            if asyncio.iscoroutine(result):
                await result
        if hasattr(instance, "cleanup"):
            result = instance.cleanup()
            if asyncio.iscoroutine(result):
                await result
        if hasattr(instance, "cleanup_audio_files"):
            instance.cleanup_audio_files()
    except Exception:
        # 校验阶段的清理异常不影响结果
        pass


async def _cleanup_modules(modules: Dict[str, Any]) -> None:
    for instance in modules.values():
        await _cleanup_instance(instance)


async def validate_config_components(
    config: Dict[str, Any], logger=None
) -> Tuple[bool, str]:
    """
    预初始化选中组件用于校验配置，捕获配置/密钥类错误。
    返回 (是否通过, 错误信息)。
    """
    logger = logger or setup_logging()
    ok, msg = _validate_selected_modules(config)
    if not ok:
        return False, msg

    selected = config.get("selected_module", {})
    init_vad = bool(selected.get("VAD"))
    init_asr = bool(selected.get("ASR"))
    asr_type = None
    selected_asr = selected.get("ASR")
    if selected_asr:
        asr_config = config.get("ASR", {}).get(selected_asr, {})
        asr_type = asr_config.get("type", selected_asr)
        if SharedASRManager.is_local_model_type(asr_type):
            init_asr = False
    init_llm = bool(selected.get("LLM"))
    init_tts = bool(selected.get("TTS"))
    init_memory = bool(selected.get("Memory"))
    init_intent = bool(selected.get("Intent"))

    modules: Dict[str, Any] = {}
    manager = None
    try:
        modules = initialize_modules(
            logger,
            config,
            init_vad,
            init_asr,
            init_llm,
            init_tts,
            init_memory,
            init_intent,
        )
        if selected_asr and asr_type and SharedASRManager.is_local_model_type(asr_type):
            manager = SharedASRManager(config, asr_type)
            await manager.initialize()
        return True, ""
    except Exception as e:
        logger.error(f"配置校验失败: {e}")
        return False, str(e)
    finally:
        if manager:
            try:
                await manager.shutdown()
            except Exception:
                pass
        await _cleanup_modules(modules)
