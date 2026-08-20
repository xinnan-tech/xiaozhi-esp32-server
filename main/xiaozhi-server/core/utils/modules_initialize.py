from typing import Dict, Any
from config.logger import setup_logging
from core.utils import tts, llm, intent, memory, vad, asr

TAG = __name__
logger = setup_logging()


def initialize_modules(
    logger,
    config: Dict[str, Any],
    init_vad=False,
    init_asr=False,
    init_llm=False,
    init_tts=False,
    init_memory=False,
    init_intent=False,
) -> Dict[str, Any]:
    modules = {}

    if init_tts:
        select_tts_module = config["selected_module"]["TTS"]
        modules["tts"] = initialize_tts(config)
        logger.bind(tag=TAG).info(f"初始化组件: tts成功 {select_tts_module}")

    if init_llm:
        select_llm_module = config["selected_module"]["LLM"]
        selected_config = config["LLM"][select_llm_module].copy()
        llm_type = selected_config.get("type", select_llm_module)

        if llm_type == "hybrid_router":
            for role in ("chat", "tool", "router"):
                model_id = selected_config.get(f"{role}_model")
                # The manager API returns the selected model and its direct
                # dependencies, but may omit a nested hybrid backend. The
                # hybrid config carries that backend as a fallback.
                model_config = config["LLM"].get(model_id) or selected_config.get(
                    f"{role}_provider_config"
                )
                if not model_config:
                    raise ValueError(
                        f"Hybrid router is missing a valid {role}_model: {model_id}"
                    )
                selected_config[f"{role}_provider_type"] = selected_config.get(
                    f"{role}_provider_type", model_config.get("type", model_id)
                )
                selected_config[f"{role}_provider_config"] = model_config.copy()

        modules["llm"] = llm.create_instance(llm_type, selected_config)
        logger.bind(tag=TAG).info(f"初始化组件: llm成功 {select_llm_module}")

    if init_intent:
        select_intent_module = config["selected_module"]["Intent"]
        intent_type = (
            select_intent_module
            if "type" not in config["Intent"][select_intent_module]
            else config["Intent"][select_intent_module]["type"]
        )
        modules["intent"] = intent.create_instance(
            intent_type, config["Intent"][select_intent_module]
        )
        logger.bind(tag=TAG).info(f"初始化组件: intent成功 {select_intent_module}")

    if init_memory:
        select_memory_module = config["selected_module"]["Memory"]
        memory_type = (
            select_memory_module
            if "type" not in config["Memory"][select_memory_module]
            else config["Memory"][select_memory_module]["type"]
        )
        modules["memory"] = memory.create_instance(
            memory_type,
            config["Memory"][select_memory_module],
            config.get("summaryMemory", None),
        )

    if init_vad:
        select_vad_module = config["selected_module"]["VAD"]
        vad_type = (
            select_vad_module
            if "type" not in config["VAD"][select_vad_module]
            else config["VAD"][select_vad_module]["type"]
        )
        modules["vad"] = vad.create_instance(vad_type, config["VAD"][select_vad_module])

    if init_asr:
        select_asr_module = config["selected_module"]["ASR"]
        modules["asr"] = initialize_asr(config)
        logger.bind(tag=TAG).info(f"初始化组件: asr成功 {select_asr_module}")
    return modules


def initialize_tts(config):
    select_tts_module = config["selected_module"]["TTS"]
    tts_config = config["TTS"][select_tts_module].copy()
    tts_config.setdefault("tts_timeout", config.get("tts_timeout", 15))
    tts_type = tts_config.get("type", select_tts_module)
    return tts.create_instance(
        tts_type,
        tts_config,
        str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
    )


def initialize_asr(config):
    select_asr_module = config["selected_module"]["ASR"]
    asr_config = config["ASR"][select_asr_module]
    asr_type = asr_config.get("type", select_asr_module)
    new_asr = asr.create_instance(
        asr_type,
        asr_config,
        str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
    )
    logger.bind(tag=TAG).info("ASR模块初始化完成")
    return new_asr


def initialize_voiceprint(asr_instance, config):
    voiceprint_config = config.get("voiceprint")
    if not voiceprint_config:
        return False
    if not voiceprint_config.get("url") or not voiceprint_config.get("speakers"):
        logger.bind(tag=TAG).warning("声纹识别配置不完整")
        return False
    try:
        asr_instance.init_voiceprint(voiceprint_config)
        logger.bind(tag=TAG).info("ASR模块声纹识别功能已动态启用")
        logger.bind(tag=TAG).info(f"配置说话人数量: {len(voiceprint_config['speakers'])}")
        return True
    except Exception as error:
        logger.bind(tag=TAG).error(f"动态初始化声纹识别功能失败: {str(error)}")
        return False
