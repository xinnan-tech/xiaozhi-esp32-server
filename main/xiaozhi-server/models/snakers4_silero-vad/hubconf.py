# 定义依赖库
dependencies = ['torch', 'torchaudio']  # 依赖的库包括 PyTorch 和 torchaudio

# 导入必要的库
import torch  # PyTorch 深度学习框架
import os  # 用于处理文件路径和目录
import sys  # 用于系统相关的操作，如修改 Python 路径

# 将当前脚本所在目录的 'src' 文件夹添加到 Python 路径中
# 这样可以直接从 'src' 目录中导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 从 silero_vad 工具库中导入必要的函数和类
from silero_vad.utils_vad import (
    init_jit_model,  # 初始化 JIT 模型
    get_speech_timestamps,  # 获取语音时间戳
    save_audio,  # 保存音频文件
    read_audio,  # 读取音频文件
    VADIterator,  # 语音活动检测迭代器
    collect_chunks,  # 收集语音片段
    OnnxWrapper  # ONNX 模型封装器
)


def versiontuple(v):
    """将版本号字符串转换为元组形式，便于比较版本号。
    
    参数:
        v (str): 版本号字符串，例如 '1.12.0' 或 '2.0.0+cu102'
    
    返回:
        tuple: 版本号的元组形式，例如 (1, 12, 0)
    """
    splitted = v.split('+')[0].split(".")  # 去掉版本号中的附加信息（如 '+cu102'），并按 '.' 分割
    version_list = []
    for i in splitted:
        try:
            version_list.append(int(i))  # 将每个部分转换为整数
        except:
            version_list.append(0)  # 如果转换失败，则默认为 0
    return tuple(version_list)  # 返回元组形式的版本号


def silero_vad(onnx=False, force_onnx_cpu=False, opset_version=16):
    """Silero 语音活动检测器 (VAD)
    
    返回一个模型及其工具函数。
    更多使用示例请参考：https://github.com/snakers4/silero-vad
    
    参数:
        onnx (bool): 是否使用 ONNX 格式的模型，默认为 False
        force_onnx_cpu (bool): 是否强制 ONNX 模型在 CPU 上运行，默认为 False
        opset_version (int): ONNX 模型的 opset 版本，默认为 16
    
    返回:
        model: 加载的 VAD 模型
        utils: 包含工具函数的元组，包括：
            - get_speech_timestamps: 获取语音时间戳
            - save_audio: 保存音频文件
            - read_audio: 读取音频文件
            - VADIterator: 语音活动检测迭代器
            - collect_chunks: 收集语音片段
    """
    available_ops = [15, 16]  # 支持的 ONNX opset 版本
    if onnx and opset_version not in available_ops:
        raise Exception(f'Available ONNX opset_version: {available_ops}')  # 如果 opset 版本不支持，抛出异常

    if not onnx:
        # 如果不是 ONNX 模式，检查 PyTorch 版本是否满足要求
        installed_version = torch.__version__  # 获取当前安装的 PyTorch 版本
        supported_version = '1.12.0'  # 支持的最低 PyTorch 版本
        if versiontuple(installed_version) < versiontuple(supported_version):
            raise Exception(f'Please install torch {supported_version} or greater ({installed_version} installed)')

    # 定义模型文件所在的目录
    model_dir = os.path.join(os.path.dirname(__file__), 'src', 'silero_vad', 'data')

    if onnx:
        # 如果是 ONNX 模式，加载 ONNX 模型
        if opset_version == 16:
            model_name = 'silero_vad.onnx'  # 默认 ONNX 模型文件名
        else:
            model_name = f'silero_vad_16k_op{opset_version}.onnx'  # 其他 opset 版本的模型文件名
        model = OnnxWrapper(os.path.join(model_dir, model_name), force_onnx_cpu)  # 加载 ONNX 模型
    else:
        # 如果不是 ONNX 模式，加载 JIT 模型
        model = init_jit_model(os.path.join(model_dir, 'silero_vad.jit'))

    # 定义工具函数元组
    utils = (
        get_speech_timestamps,  # 获取语音时间戳
        save_audio,  # 保存音频文件
        read_audio,  # 读取音频文件
        VADIterator,  # 语音活动检测迭代器
        collect_chunks  # 收集语音片段
    )

    # 返回模型和工具函数
    return model, utils