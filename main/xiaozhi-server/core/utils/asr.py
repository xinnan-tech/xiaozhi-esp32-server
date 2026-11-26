import importlib
import json
import logging
import os
import sys
import threading
import time
import wave
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 本地 ASR：模型常驻内存，单个实例几百 MB ~ 3 GB（FunASR / SenseVoice 约 3 GB）。
# 同一份配置只加载一次并全进程共享，避免每个 WebSocket 连接各拉一个实例，
# 设备快速连断多次就把内存吃满甚至拖死整台机器（#3365）。
#
# 只收录"每次调用都自建流/上下文"的 provider：
#   - fun_local        : AutoModel.generate 每次传新 cache，串行化后安全
#   - sherpa_onnx_local: 每次 create_stream()，模型本身无状态
# vosk 暂不收录：它的 KaldiRecognizer 在实例上跨调用累积波形状态且非线程安全，
# 多连接共用一个 recognizer 会互相串音（vosk 模型只有几十 MB，复用的收益有限）。
LOCAL_ASR_TYPES = {"fun_local", "sherpa_onnx_local"}

_LOCAL_ASR_CACHE: dict = {}
_LOCAL_ASR_CACHE_LOCK = threading.Lock()


def _cache_key(class_name: str, args, kwargs):
    try:
        config = args[0] if len(args) > 0 else kwargs.get("config")
        # delete_audio_file 等其余构造参数也要进 key，
        # 否则参数不同的两次创建会复用同一个实例
        payload = [config, *args[1:]] if len(args) > 0 else [config]
        return class_name + ":" + json.dumps(payload, sort_keys=True, default=str)
    except Exception:
        return None


def cached_local_instance(class_name: str, factory, args, kwargs):
    """按「类型 + 配置」复用本地 ASR 实例；非本地类型直接新建。

    首次创建时持锁，避免并发连接同时加载模型造成内存翻倍。
    """
    key = _cache_key(class_name, args, kwargs)
    if key is None:
        return factory()
    with _LOCAL_ASR_CACHE_LOCK:
        instance = _LOCAL_ASR_CACHE.get(key)
        if instance is not None:
            logger.bind(tag=TAG).info(
                f"复用已加载的本地 ASR 实例: {class_name}（不再为每条连接重复占用内存）"
            )
            return instance
        instance = factory()
        _LOCAL_ASR_CACHE[key] = instance
        return instance


def clear_local_cache():
    """释放本地 ASR 缓存（测试与热重载用）。"""
    with _LOCAL_ASR_CACHE_LOCK:
        _LOCAL_ASR_CACHE.clear()


def create_instance(class_name: str, *args, **kwargs) -> ASRProviderBase:
    """工厂方法创建ASR实例"""
    if os.path.exists(os.path.join('core', 'providers', 'asr', f'{class_name}.py')):
        lib_name = f'core.providers.asr.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')

        def _build():
            return sys.modules[lib_name].ASRProvider(*args, **kwargs)

        if class_name in LOCAL_ASR_TYPES:
            return cached_local_instance(class_name, _build, args, kwargs)
        return _build()

    raise ValueError(f"不支持的ASR类型: {class_name}，请检查该配置的type是否设置正确")
