dependencies = ['torch', 'torchaudio']
import torch
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from silero_vad.utils_vad import (init_jit_model,
                                  get_speech_timestamps,
                                  save_audio,
                                  read_audio,
                                  VADIterator,
                                  collect_chunks,
                                  OnnxWrapper)


def versiontuple(v):
    splitted = v.split('+')[0].split(".")
    version_list = []
    for i in splitted:
        try:
            version_list.append(int(i))
        except:
            version_list.append(0)
    return tuple(version_list)


def silero_vad(onnx=False, force_onnx_cpu=False, opset_version=16):
    """Silero Voice Activity Detector
    Returns a model with a set of utils
    Please see https://github.com/snakers4/silero-vad for usage examples
    """
    available_ops = [15, 16]
    if onnx and opset_version not in available_ops:
        raise Exception(f'Available ONNX opset_version: {available_ops}')

    if not onnx:
        installed_version = torch.__version__
        supported_version = '1.12.0'
        if versiontuple(installed_version) < versiontuple(supported_version):
            raise Exception(f'Please install torch {supported_version} or greater ({installed_version} installed)')

    model_dir = os.path.join(os.path.dirname(__file__), 'src', 'silero_vad', 'data')
    if onnx:
        if opset_version == 16:
            model_name = 'silero_vad.onnx'
        else:
            model_name = f'silero_vad_16k_op{opset_version}.onnx'
        model = OnnxWrapper(os.path.join(model_dir, model_name), force_onnx_cpu)
    else:
        model = init_jit_model(os.path.join(model_dir, 'silero_vad.jit'))
    utils = (get_speech_timestamps,
             save_audio,
             read_audio,
             VADIterator,
             collect_chunks)

    return model, utils
