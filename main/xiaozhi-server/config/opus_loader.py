# 在导入 opuslib 之前处理 opus 动态库
import ctypes
import ctypes.util
import os
import platform
import sys
from enum import Enum
from pathlib import Path
from typing import cast

from config.logger import setup_logging

APP_DIR = str(Path(__file__).resolve().parent.parent)

logger = setup_logging()


class Platform(Enum):
    WINDOWS = "windows"
    MACOS = "darwin"
    LINUX = "linux"


class Arch(Enum):
    WINDOWS = {"arm": "arm64", "intel": "x64"}
    MACOS = {"arm": "arm64", "intel": "x64"}
    LINUX = {"arm": "arm64", "intel": "x64"}


class OpusInfo(Enum):
    WINDOWS = {"name": "opus.dll", "system_name": ["opus"]}
    MACOS = {"name": "libopus.dylib", "system_name": ["libopus.dylib"]}
    LINUX = {"name": "libopus.so", "system_name": ["libopus.so.0", "libopus.so"]}


def _get_platform_dict() -> dict[Platform, dict]:
    """获取平台映射字典"""
    return {
        Platform.WINDOWS: {
            "arch": Arch.WINDOWS,
            "lib_info": OpusInfo.WINDOWS,
            "dir": "win",
        },
        Platform.MACOS: {
            "arch": Arch.MACOS,
            "lib_info": OpusInfo.MACOS,
            "dir": "mac",
        },
        Platform.LINUX: {
            "arch": Arch.LINUX,
            "lib_info": OpusInfo.LINUX,
            "dir": "linux",
        },
    }


def get_platform() -> Platform:
    """获取当前平台"""
    system = platform.system().lower()
    if system in ("windows", "win32", "cygwin"):
        return Platform.WINDOWS
    if system == "darwin":
        return Platform.MACOS
    return Platform.LINUX


def get_arch(system: Platform) -> tuple[str, str]:
    """获取当前架构

    Args:
        system: 平台枚举值

    Returns:
        (原始架构字符串, 标准化架构名称)
    """
    architecture = platform.machine().lower()
    is_arm = "arm" in architecture or "aarch64" in architecture

    platform_dict = _get_platform_dict()
    arch_map = platform_dict[system]["arch"].value
    arch_name = arch_map["arm" if is_arm else "intel"]

    return architecture, arch_name


def get_lib_name(system: Platform, local: bool = True) -> str | list[str]:
    """根据平台架构获取 Opus 库名称"""
    key = "name" if local else "system_name"
    platform_dict = _get_platform_dict()
    return platform_dict[system]["lib_info"].value[key]


def get_system_info() -> tuple[Platform, str]:
    """获取当前系统信息

    Returns:
        (平台, 架构名称)
    """
    system = get_platform()
    _, arch_name = get_arch(system)
    logger.info(f"检测到平台架构: {system.value} {arch_name}")
    return system, arch_name


def _build_lib_candidates(
    base_libs_path: Path, system_dir: str, arch_name: str
) -> list[Path]:
    """构建库目录候选路径列表（按优先级排序）

    Args:
        base_libs_path: 基础 libs 目录路径
        system_dir: 系统目录名称（如 win、mac、linux）
        arch_name: 架构名称（如 x64、arm64）

    Returns:
        候选路径列表（按优先级排序）
    """
    candidates = []

    # 优先级 1: 特定平台和架构的目录
    specific_path = base_libs_path / system_dir / arch_name
    if specific_path.is_dir():
        candidates.append(specific_path)

    # 优先级 2: 特定平台的目录
    platform_path = base_libs_path / system_dir
    if platform_path.is_dir() and platform_path not in candidates:
        candidates.append(platform_path)

    # 优先级 3: 基础 libs 目录
    if base_libs_path.is_dir() and base_libs_path not in candidates:
        candidates.append(base_libs_path)

    return candidates


def get_search_paths(system: Platform, arch_name: str) -> list[tuple[str, str]]:
    """获取库文件搜索路径列表

    按优先级：特定平台/架构 > 特定平台 > 通用 > 项目根目录

    Args:
        system: 平台枚举值
        arch_name: 架构名称

    Returns:
        (目录路径, 文件名) 元组列表
    """
    lib_name = cast(str, get_lib_name(system))
    search_paths: list[tuple[str, str]] = []

    platform_dict = _get_platform_dict()
    system_dir = platform_dict[system]["dir"]
    base_libs_path = Path(APP_DIR) / "libs"

    # 如果 libs 目录不存在，直接返回项目根目录
    if not base_libs_path.is_dir():
        logger.debug(f"未找到 libs 目录: {base_libs_path}")
        return [(APP_DIR, lib_name)]

    # 候选路径列表
    lib_candidates = _build_lib_candidates(base_libs_path, system_dir, arch_name)
    for lib_path in lib_candidates:
        search_paths.append((str(lib_path), lib_name))
        logger.debug(f"找到 libs 目录: {lib_path}")

    # 添加项目根目录作为最后的备选
    if not search_paths or APP_DIR not in [s[0] for s in search_paths]:
        search_paths.append((APP_DIR, lib_name))

    # 调试日志：显示所有搜索路径
    for dir_path, filename in search_paths:
        full_path = os.path.join(dir_path, filename)
        exists = os.path.exists(full_path)
        logger.debug(f"搜索路径: {full_path} (存在: {exists})")

    return search_paths


def find_system_opus(system: Platform) -> str:
    """从系统路径查找 Opus 库

    Args:
        system: 平台枚举值

    Returns:
        找到的库路径，未找到返回空字符串
    """
    lib_names = get_lib_name(system, local=False)

    if isinstance(lib_names, str):
        lib_names = [lib_names]

    for lib_name in lib_names:
        try:
            system_lib_path = ctypes.util.find_library(lib_name)
            if system_lib_path:
                logger.info(f"在系统路径中找到 Opus 库: {system_lib_path}")
                return system_lib_path

            # 直接尝试加载库名
            _ = ctypes.cdll.LoadLibrary(lib_name)
            logger.info(f"直接加载系统 Opus 库: {lib_name}")
            return lib_name

        except (OSError, TypeError) as e:
            logger.debug(f"加载系统库失败: {lib_name} - {e}")
            continue

    logger.debug("在系统中未找到 Opus 库")
    return ""


def _find_local_opus(system: Platform, arch_name: str) -> str | None:
    """从本地搜索路径查找 Opus 库

    Args:
        system: 平台枚举值
        arch_name: 架构名称

    Returns:
        找到的库文件路径，未找到返回 None
    """
    search_paths = get_search_paths(system, arch_name)

    for dir_path, file_name in search_paths:
        full_path = os.path.join(dir_path, file_name)
        if os.path.exists(full_path):
            return str(full_path)
    return None


def _setup_dll_search_path(system: Platform, lib_dir: str) -> None:
    """在Windows上设置DLL搜索路径

    Args:
        system: 平台枚举值
        lib_dir: 库文件所在目录
    """
    if system != Platform.WINDOWS or not lib_dir:
        return

    try:
        if hasattr(os, "add_dll_directory"):
            dll_dir_handle = os.add_dll_directory(lib_dir)
            setattr(sys, "_opus_dll_dir_handle", dll_dir_handle)
            logger.debug(f"已添加DLL搜索路径: {lib_dir}")
    except OSError as e:
        logger.warning(f"添加DLL搜索路径失败: {e}")

    os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")


def _patch_find_library(lib_name: str, lib_path: str) -> None:
    """修补 ctypes.util.find_library 函数，确保 opuslib_next 能找到 opus 库

    Args:
        lib_name: 库名称
        lib_path: 库文件路径
    """
    original_find_library = ctypes.util.find_library

    def patched_find_library(name: str) -> str | None:
        if name == lib_name:
            return lib_path
        return original_find_library(name)

    ctypes.util.find_library = patched_find_library


def _load_opus_library(lib_path: str) -> bool:
    """尝试加载 opus 库"""
    try:
        # 加载库并持久化句柄到 sys 属性，防止被垃圾回收释放库句柄
        cdll_instance = ctypes.CDLL(lib_path)
        setattr(sys, "_opus_cdll", cdll_instance)
        logger.info(f"成功加载 Opus 库: {lib_path}")
        setattr(sys, "_opus_loaded", True)
        return True
    except OSError as e:
        logger.error(f"加载 Opus 库失败: {lib_path} - {e}")
        return False


def setup_opus() -> bool:
    """加载 Opus 动态库 - 优先级：系统库 > 本地库

    Returns:
        加载成功返回True，否则返回False
    """
    # 检查 Opus 库是否已在当前进程中完成加载，避免重复初始化
    if hasattr(sys, "_opus_loaded"):
        logger.info("Opus 库已加载，跳过重复初始化")

    system, arch_name = get_system_info()
    final_lib_path = ""

    logger.info("尝试从系统路径加载 Opus 库")
    system_lib_path = find_system_opus(system)

    if system_lib_path:
        # 1. 尝试从系统路径加载
        logger.info(f"在系统中找到 Opus 库: {system_lib_path}")
        final_lib_path = system_lib_path
    else:
        # 2. 尝试从本地搜索路径查找
        logger.info("系统路径未找到，尝试从本地加载 Opus 库")
        local_lib_path = _find_local_opus(system, arch_name)

        if local_lib_path:
            lib_dir = str(Path(local_lib_path).parent)
            _setup_dll_search_path(system, lib_dir)
            final_lib_path = local_lib_path
        else:
            logger.debug("本地未找到本地 Opus 库文件")

    # 打补丁确保 opuslib_next 能找到正确的库路径
    if final_lib_path:
        loaded = _load_opus_library(final_lib_path)
        if loaded:
            _patch_find_library("opus", final_lib_path)
        return loaded

    logger.error("无法加载 Opus 库")
    return False
