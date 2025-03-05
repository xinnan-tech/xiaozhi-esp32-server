from .utils_vad import init_jit_model, OnnxWrapper
import torch
torch.set_num_threads(1)


def load_silero_vad(onnx=False, opset_version=16):
    available_ops = [15, 16]
    if onnx and opset_version not in available_ops:
        raise Exception(f'Available ONNX opset_version: {available_ops}')

    if onnx:
        if opset_version == 16:
            model_name = 'silero_vad.onnx'
        else:
            model_name = f'silero_vad_16k_op{opset_version}.onnx'
    else:
        model_name = 'silero_vad.jit'
    package_path = "silero_vad.data"

    try:
        import importlib_resources as impresources
        model_file_path = str(impresources.files(package_path).joinpath(model_name))
    except:
        from importlib import resources as impresources
        try:
            with impresources.path(package_path, model_name) as f:
                model_file_path = f
        except:
            model_file_path = str(impresources.files(package_path).joinpath(model_name))

    if onnx:
        model = OnnxWrapper(model_file_path, force_onnx_cpu=True)
    else:
        model = init_jit_model(model_file_path)

    return model
