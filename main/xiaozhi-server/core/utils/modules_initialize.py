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
    Initialize all module components.
    """
    modules = {}

    if init_tts:
        select_tts_module = config["selected_module"]["TTS"]
        modules["tts"] = initialize_tts(config)
        logger.bind(tag=TAG).info(f"Component initialized: TTS success {select_tts_module}")

    if init_llm:
        select_llm_module = config["selected_module"]["LLM"]
        llm_type = select_llm_module if "type" not in config["LLM"][select_llm_module] else config["LLM"][select_llm_module]["type"]
        modules["llm"] = llm.create_instance(llm_type, config["LLM"][select_llm_module])
        logger.bind(tag=TAG).info(f"Component initialized: LLM success {select_llm_module}")

    # FIX: Lowercase 'intent' to match your config.yaml
    if init_intent:
        select_intent_module = config["selected_module"]["Intent"]
        intent_type = (
            select_intent_module
            if "type" not in config["Intent"][select_intent_module]
            else config["Intent"][select_intent_module]["type"]
        )
        modules["Intent"] = intent.create_instance(
            intent_type,
            config["Intent"][select_intent_module],
        )
        logger.bind(tag=TAG).info(f"Component initialized: Intent success {select_intent_module}")

    if init_memory:
        select_memory_module = config["selected_module"]["Memory"]
        memory_type = select_memory_module if "type" not in config["Memory"][select_memory_module] else config["Memory"][select_memory_module]["type"]
        modules["memory"] = memory.create_instance(memory_type, config["Memory"][select_memory_module], config.get("summaryMemory", None))
        logger.bind(tag=TAG).info(f"Component initialized: Memory success {select_memory_module}")

    if init_vad:
        select_vad_module = config["selected_module"]["VAD"]
        vad_type = select_vad_module if "type" not in config["VAD"][select_vad_module] else config["VAD"][select_vad_module]["type"]
        modules["vad"] = vad.create_instance(vad_type, config["VAD"][select_vad_module])
        logger.bind(tag=TAG).info(f"Component initialized: VAD success {select_vad_module}")

    if init_asr:
        modules["asr"] = initialize_asr(config)
        
    return modules

# Global cache for ASR and TTS instances
ASR_INSTANCES = {}
TTS_INSTANCES = {}

def initialize_tts(config, use_cache=True):
    select_tts_module = config["selected_module"]["TTS"]
    
    # Check cache first (only if requested)
    if use_cache and select_tts_module in TTS_INSTANCES:
        logger.bind(tag=TAG).debug(f"Using cached TTS instance: {select_tts_module}")
        return TTS_INSTANCES[select_tts_module]

    tts_type = select_tts_module if "type" not in config["TTS"][select_tts_module] else config["TTS"][select_tts_module]["type"]
    new_tts = tts.create_instance(tts_type, config["TTS"][select_tts_module], str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"))
    
    # Cache the new instance (only if not a private override)
    if use_cache:
        TTS_INSTANCES[select_tts_module] = new_tts
        logger.bind(tag=TAG).info(f"Component initialized and cached: TTS success {select_tts_module}")
    else:
        logger.bind(tag=TAG).info(f"Private Component initialized (not cached): TTS success {select_tts_module}")
        
    return new_tts

def initialize_asr(config, use_cache=True):
    select_asr_module = config["selected_module"]["ASR"]
    
    # Check cache first (only if requested)
    if use_cache and select_asr_module in ASR_INSTANCES:
        logger.bind(tag=TAG).debug(f"Using cached ASR instance: {select_asr_module}")
        return ASR_INSTANCES[select_asr_module]

    asr_type = select_asr_module if "type" not in config["ASR"][select_asr_module] else config["ASR"][select_asr_module]["type"]
    new_asr = asr.create_instance(asr_type, config["ASR"][select_asr_module], str(config.get("delete_audio", True)).lower() in ("true", "1", "yes"))
    
    # Cache the new instance (only if not a private override)
    if use_cache:
        ASR_INSTANCES[select_asr_module] = new_asr
        logger.bind(tag=TAG).info(f"Component initialized and cached: ASR success {select_asr_module}")
    else:
        logger.bind(tag=TAG).info(f"Private Component initialized (not cached): ASR success {select_asr_module}")
        
    return new_asr

def initialize_voiceprint(asr_instance, config):
    """Initialize voiceprint identification"""
    voiceprint_config = config.get("voiceprint")
    if not voiceprint_config or not voiceprint_config.get("url") or not voiceprint_config.get("speakers"):
        return False
    try:
        asr_instance.init_voiceprint(voiceprint_config)
        logger.bind(tag=TAG).info("Voiceprint recognition enabled")
        return True
    except Exception as e:
        logger.bind(tag=TAG).error(f"Voiceprint initialization failed: {str(e)}")
        return False

