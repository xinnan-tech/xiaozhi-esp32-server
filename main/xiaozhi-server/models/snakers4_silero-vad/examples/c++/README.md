# Silero-VAD V6 in C++ (based on LibTorch)

This is the source code for Silero-VAD V6 in C++, utilizing LibTorch & Onnxruntime. 
You should compare its results with the Python version. 
Results at 16 and 8kHz have been tested. Batch and CUDA inference options are deprecated. 


## Requirements
- GCC 11.4.0 (GCC >= 5.1)
- Onnxruntime 1.11.0 (other versions are also acceptable)
- LibTorch 1.13.0 (other versions are also acceptable)

## Download LibTorch

```bash
-Onnxruntime
$wget https://github.com/microsoft/onnxruntime/releases/download/v1.11.1/onnxruntime-linux-x64-1.11.1.tgz
$tar -xvf onnxruntime-linux-x64-1.11.1.tgz
$ln -s onnxruntime-linux-x64-1.11.1 onnxruntime-linux    #soft-link

-Libtorch
$wget https://download.pytorch.org/libtorch/cpu/libtorch-shared-with-deps-1.13.0%2Bcpu.zip
$unzip libtorch-shared-with-deps-1.13.0+cpu.zip
```

## Compilation

```bash
-ONNX-build
$g++ main.cc silero.cc -I ./onnxruntime-linux/include/ -L ./onnxruntime-linux/lib/ -lonnxruntime -Wl,-rpath,./onnxruntime-linux/lib/ -o silero -std=c++14 -D_GLIBCXX_USE_CXX11_ABI=0 -DUSE_ONNX

-TORCH-build
$g++ main.cc silero.cc -I ./libtorch/include/ -I ./libtorch/include/torch/csrc/api/include -L ./libtorch/lib/ -ltorch -ltorch_cpu -lc10 -Wl,-rpath,./libtorch/lib/ -o silero -std=c++14 -D_GLIBCXX_USE_CXX11_ABI=0 -DUSE_TORCH
```

## Optional Compilation Flags
-DUSE_TORCH
-DUSE_ONNX

## Run the Program
To run the program, use the following command:

`./silero <sample.wav> <SampleRate> <threshold>`
`./silero aepyx.wav 16000 0.5`
`./silero aepyx_8k.wav 8000 0.5`

The sample file aepyx.wav is part of the Voxconverse dataset.
File details: aepyx.wav is a 16kHz, 16-bit audio file.
File details: aepyx_8k.wav is a 8kHz, 16-bit audio file.
