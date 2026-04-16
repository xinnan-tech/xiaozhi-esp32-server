# 在导入 opuslib 之前处理 opus 动态库
import ctypes
import os
import platform
import shutil
import sys
from enum import Enum

# 获取日志记录器
from logging import getLogger
from pathlib import Path
from typing import cast

from .constant import APP_DIR

logger = getLogger(__name__)


# 平台常量定义
class PLATFORM(Enum):
    WINDOWS = "windows"
    MACOS = "darwin"
    LINUX = "linux"


# 架构常量定义
class ARCH(Enum):
    WINDOWS = {"arm": "x64", "intel": "x64"}
    MACOS = {"arm": "arm64", "intel": "x64"}
    LINUX = {"arm": "arm64", "intel": "x64"}


# 动态链接库路径常量定义
class LIB_PATH(Enum):
    WINDOWS = "libs/win/x64"
    MACOS = "libs/mac/{arch}"
    LINUX = "libs/linux/{arch}"


# 动态链接库名称常量定义
class LIB_INFO(Enum):
    WINDOWS = {"name": "opus.dll", "system_name": ["opus"]}
    MACOS = {"name": "libopus.dylib", "system_name": ["libopus.dylib"]}
    LINUX = {"name": "libopus.so", "system_name": ["libopus.so.0", "libopus.so"]}


def get_platform() -> PLATFORM:
    system = platform.system().lower()
    if system == "windows" or system.startswith("win"):
        system = PLATFORM.WINDOWS
    elif system == "darwin":
        system = PLATFORM.MACOS
    else:
        system = PLATFORM.LINUX
    return system


def get_arch(system: PLATFORM) -> tuple[str, str]:
    architecture = platform.machine().lower()
    is_arm = "arm" in architecture or "aarch64" in architecture
    if system == PLATFORM.WINDOWS:
        arch_name = ARCH.WINDOWS.value["arm" if is_arm else "intel"]
    elif system == PLATFORM.MACOS:
        arch_name = ARCH.MACOS.value["arm" if is_arm else "intel"]
    else:
        arch_name = ARCH.LINUX.value["arm" if is_arm else "intel"]
    return architecture, arch_name


def get_lib_path(system: PLATFORM, arch_name: str):
    if system == PLATFORM.WINDOWS:
        lib_name = LIB_PATH.WINDOWS.value
    elif system == PLATFORM.MACOS:
        lib_name = LIB_PATH.MACOS.value.format(arch=arch_name)
    else:
        lib_name = LIB_PATH.LINUX.value.format(arch=arch_name)
    return lib_name


def get_lib_name(system: PLATFORM, local: bool = True) -> str | list[str]:
    """获取库名称.

    Args:
        system (PLATFORM): 平台
        local (bool, optional): 是否获取本地名称(str), 默认为 True. 如果为 False, 则获取系统名称列表(list).

    Returns:
        str | list: 库名称
    """
    key = "name" if local else "system_name"
    if system == PLATFORM.WINDOWS:
        lib_name = LIB_INFO.WINDOWS.value[key]
    elif system == PLATFORM.MACOS:
        lib_name = LIB_INFO.MACOS.value[key]
    else:
        lib_name = LIB_INFO.LINUX.value[key]
    return lib_name


def get_system_info() -> tuple[PLATFORM, str]:
    """
    获取当前系统信息.
    """
    # 标准化系统名称
    system = get_platform()

    # 标准化架构名称
    _, arch_name = get_arch(system)
    logger.info(f"检测到系统: {system}, 架构: {arch_name}")

    return system, arch_name


def get_search_paths(system: PLATFORM, arch_name: str) -> list[tuple[str, str]]:
    """
    获取库文件搜索路径列表（使用统一的资源查找器）
    """
    from .finder import find_libs_dir

    lib_name = cast(str, get_lib_name(system))

    search_paths: list[tuple[str, str]] = []

    # 映射系统名称到目录名称
    system_dir_map = {
        PLATFORM.WINDOWS: "win",
        PLATFORM.MACOS: "mac",
        PLATFORM.LINUX: "linux",
    }

    system_dir = system_dir_map.get(system)

    # 首先尝试查找特定平台和架构的libs目录
    if system_dir:
        specific_libs_dir = find_libs_dir(system_dir, arch_name)
        if specific_libs_dir:
            search_paths.append((specific_libs_dir, lib_name))
            logger.debug(f"找到特定平台架构libs目录: {specific_libs_dir}")

    # 然后查找特定平台的libs目录
    if system_dir:
        platform_libs_dir = find_libs_dir(system_dir)
        if platform_libs_dir:
            search_paths.append((platform_libs_dir, lib_name))
            logger.debug(f"找到特定平台libs目录: {platform_libs_dir}")

    # 查找通用libs目录
    general_libs_dir = find_libs_dir()
    if general_libs_dir:
        search_paths.append((general_libs_dir, lib_name))
        logger.debug(f"添加通用libs目录: {general_libs_dir}")

    # 添加项目根目录作为最后的备选
    project_root = APP_DIR
    search_paths.append((project_root, lib_name))

    # 打印所有搜索路径，帮助调试
    for dir_path, filename in search_paths:
        full_path = os.path.join(dir_path, filename)
        logger.debug(f"搜索路径: {full_path} (存在: {os.path.exists(full_path)})")
    return search_paths


def find_system_opus() -> str:
    """
    从系统路径查找opus库.
    """
    system, _ = get_system_info()
    lib_path = ""

    try:
        # 获取系统上opus库的名称
        lib_names = get_lib_name(system, False)

        # 尝试加载每个可能的名称
        for lib_name in lib_names:
            try:
                # 导入ctypes.util以使用find_library函数
                import ctypes.util

                system_lib_path = ctypes.util.find_library(lib_name)

                if system_lib_path:
                    lib_path = system_lib_path
                    logger.info(f"在系统路径中找到opus库: {lib_path}")
                    break
                else:
                    # 直接尝试加载库名
                    _ = ctypes.cdll.LoadLibrary(lib_name)
                    lib_path = lib_name
                    logger.info(f"直接加载系统opus库: {lib_name}")
                    break
            except Exception as e:
                logger.debug(f"加载系统库 {lib_name} 失败: {e}")
                continue

    except Exception as e:
        logger.error(f"查找系统opus库失败: {e}")

    return lib_path


def copy_opus_to_project(system_lib_path: str):
    """
    将系统库复制到项目目录.
    """

    system, arch_name = get_system_info()

    if not system_lib_path:
        logger.error("无法复制opus库：系统库路径为空")
        return None

    try:
        # 使用resource_finder获取项目根目录
        project_root = APP_DIR

        # 获取目标目录路径 - 使用实际目录结构
        target_path = get_lib_path(system, arch_name)
        target_dir = os.path.join(project_root, target_path)

        # 创建目标目录(如果不存在)
        os.makedirs(target_dir, exist_ok=True)

        # 确定目标文件名
        lib_name = cast(str, get_lib_name(system))
        target_file = os.path.join(target_dir, lib_name)

        # 复制文件
        _ = shutil.copy2(system_lib_path, target_file)
        logger.info(f"已将opus库从 {system_lib_path} 复制到 {target_file}")

        return str(target_file)

    except Exception as e:
        logger.error(f"复制opus库到项目目录失败: {e}")
        return None


def setup_opus() -> bool:
    """
    设置opus动态库.
    """
    # 检查是否已经由runtime_hook加载
    if hasattr(sys, "_opus_loaded"):
        logger.info("opus库已由运行时钩子加载")
        return True

    # 获取当前系统信息
    system, arch_name = get_system_info()
    logger.info(f"当前系统: {system}, 架构: {arch_name}")

    # 构建搜索路径
    search_paths = get_search_paths(system, arch_name)

    # 查找本地库文件
    lib_path = ""
    lib_dir = ""

    for dir_path, file_name in search_paths:
        full_path = os.path.join(dir_path, file_name)
        if os.path.exists(full_path):
            lib_path = str(full_path)
            lib_dir = str(dir_path)
            logger.info(f"找到opus库文件: {lib_path}")
            break

    # 如果本地没找到，尝试从系统查找
    if not lib_path:
        logger.warning("本地未找到opus库文件，尝试从系统路径加载")
        system_lib_path = find_system_opus()

        if system_lib_path:
            # 首次尝试直接使用系统库
            try:
                _ = ctypes.cdll.LoadLibrary(system_lib_path)
                logger.info(f"已从系统路径加载opus库: {system_lib_path}")
                setattr(sys, "_opus_loaded", True)
                return True
            except Exception as e:
                logger.warning(f"加载系统opus库失败: {e}，尝试复制到项目目录")

            # 如果直接加载失败，尝试复制到项目目录
            lib_path = copy_opus_to_project(system_lib_path)
            if lib_path:
                lib_dir = str(Path(lib_path).parent)
            else:
                logger.error("无法找到或复制opus库文件")
                return False
        else:
            logger.error("在系统中也未找到opus库文件")
            return False

    # Windows平台特殊处理
    if system == PLATFORM.WINDOWS and lib_dir:
        # 添加DLL搜索路径
        if hasattr(os, "add_dll_directory"):
            try:
                _ = os.add_dll_directory(lib_dir)
                logger.debug(f"已添加DLL搜索路径: {lib_dir}")
            except Exception as e:
                logger.warning(f"添加DLL搜索路径失败: {e}")

        # 设置环境变量
        os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")

    # 修补库路径
    _patch_find_library("opus", lib_path)

    # 尝试加载库
    try:
        # 加载DLL并存储引用以防止垃圾回收
        _ = ctypes.CDLL(lib_path)
        logger.info(f"成功加载opus库: {lib_path}")
        setattr(sys, "_opus_loaded", True)
        return True
    except Exception as e:
        logger.error(f"加载opus库失败: {e}")
        return False


def _patch_find_library(lib_name: str, lib_path: str):
    """
    修补ctypes.util.find_library函数.
    """
    import ctypes.util

    original_find_library = ctypes.util.find_library

    def patched_find_library(name: str):
        if name == lib_name:
            return lib_path
        return original_find_library(name)

    ctypes.util.find_library = patched_find_library
