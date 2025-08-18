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
    """
    Initialize all module components

    Args:
        config: Configuration dictionary

    Returns:
        Dict[str, Any]: Dictionary containing all initialized modules
    """
    modules = {}

    # Initialize TTS module
    if init_tts:
        select_tts_module = config["selected_module"]["TTS"]
        modules["tts"] = initialize_tts(config)
        logger.bind(tag=TAG).info(f"Initialize component: tts successful {select_tts_module}")

    # Initialize LLM module
    if init_llm:
        select_llm_module = config["selected_module"]["LLM"]
        llm_type = (
            select_llm_module
            if "type" not in config["LLM"][select_llm_module]
            else config["LLM"][select_llm_module]["type"]
        )

        modules["llm"] = llm.create_instance(
            llm_type,
            config["LLM"][select_llm_module],
        )
        logger.bind(tag=TAG).info(f"Initialize component: llm successful {select_llm_module}")

    # Initialize Intent module
    if init_intent:
        select_intent_module = config["selected_module"]["Intent"]
        intent_type = (
            select_intent_module
            if "type" not in config["Intent"][select_intent_module]
            else config["Intent"][select_intent_module]["type"]
        )

        modules["intent"] = intent.create_instance(
            intent_type,
            config["Intent"][select_intent_module],
        )
        logger.bind(tag=TAG).info(f"Initialize component: intent successful {select_intent_module}")

    # Initialize Memory module
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
        logger.bind(tag=TAG).info(f"Initialize component: memory successful {select_memory_module}")

    # Initialize VAD module
    if init_vad:
        select_vad_module = config["selected_module"]["VAD"]
        vad_type = (
            select_vad_module
            if "type" not in config["VAD"][select_vad_module]
            else config["VAD"][select_vad_module]["type"]
        )

        modules["vad"] = vad.create_instance(
            vad_type,
            config["VAD"][select_vad_module],
        )
        logger.bind(tag=TAG).info(f"Initialize component: vad successful {select_vad_module}")

    # Initialize ASR module
    if init_asr:
        select_asr_module = config["selected_module"]["ASR"]
        modules["asr"] = initialize_asr(config)
        logger.bind(tag=TAG).info(f"Initialize component: asr successful {select_asr_module}")

    return modules

def initialize_tts(config):
    select_tts_module = config["selected_module"]["TTS"]
    tts_type = (
        select_tts_module
        if "type" not in config["TTS"][select_tts_module]
        else config["TTS"][select_tts_module]["type"]
    )

    new_tts = tts.create_instance(
        tts_type,
        config["TTS"][select_tts_module],
        str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
    )

    return new_tts

def initialize_asr(config):
    select_asr_module = config["selected_module"]["ASR"]
    asr_type = (
        select_asr_module
        if "type" not in config["ASR"][select_asr_module]
        else config["ASR"][select_asr_module]["type"]
    )

    # Create module config with filtering settings
    module_config = config["ASR"][select_asr_module].copy()
    # Add ASR filtering config if available
    if "filtering" in config["ASR"]:
        module_config["filtering"] = config["ASR"]["filtering"]

    new_asr = asr.create_instance(
        asr_type,
        module_config,
        str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"),
    )

    logger.bind(tag=TAG).info("ASR module initialization completed")
    return new_asr

def initialize_voiceprint(asr_instance, config):
    """Initialize voiceprint recognition functionality"""
    voiceprint_config = config.get("voiceprint")
    if not voiceprint_config:
        return False

    # Apply configuration
    if not voiceprint_config.get("url") or not voiceprint_config.get("speakers"):
        logger.bind(tag=TAG).warning("Voiceprint recognition configuration incomplete")
        return False

    try:
        asr_instance.init_voiceprint(voiceprint_config)
        logger.bind(tag=TAG).info("ASR module voiceprint recognition functionality dynamically enabled")
        logger.bind(tag=TAG).info(f"Configured speaker count: {len(voiceprint_config['speakers'])}")
        return True
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to dynamically initialize voiceprint recognition functionality: {str(e)}")
        return False
