# Silero-VAD V5 in C++ (based on LibTorch)

This is the source code for Silero-VAD V5 in C++, utilizing LibTorch. The primary implementation is CPU-based, and you should compare its results with the Python version. Only results at 16kHz have been tested.

Additionally, batch and CUDA inference options are available if you want to explore further. Note that when using batch inference, the speech probabilities may slightly differ from the standard version, likely due to differences in caching. Unlike individual input processing, batch inference may not use the cache from previous chunks. Despite this, batch inference offers significantly faster processing. For optimal performance, consider adjusting the threshold when using batch inference.

## Requirements

- GCC 11.4.0 (GCC >= 5.1)
- LibTorch 1.13.0 (other versions are also acceptable)

## Download LibTorch

```bash
-CPU Version
wget https://download.pytorch.org/libtorch/cpu/libtorch-shared-with-deps-1.13.0%2Bcpu.zip
unzip libtorch-shared-with-deps-1.13.0+cpu.zip'

-CUDA Version
wget https://download.pytorch.org/libtorch/cu116/libtorch-shared-with-deps-1.13.0%2Bcu116.zip
unzip libtorch-shared-with-deps-1.13.0+cu116.zip
```

## Compilation

```bash
-CPU Version
g++ main.cc silero_torch.cc -I ./libtorch/include/ -I ./libtorch/include/torch/csrc/api/include -L ./libtorch/lib/ -ltorch -ltorch_cpu -lc10 -Wl,-rpath,./libtorch/lib/ -o silero -std=c++14 -D_GLIBCXX_USE_CXX11_ABI=0

-CUDA Version
g++ main.cc silero_torch.cc -I ./libtorch/include/ -I ./libtorch/include/torch/csrc/api/include -L ./libtorch/lib/ -ltorch -ltorch_cuda -ltorch_cpu -lc10 -Wl,-rpath,./libtorch/lib/ -o silero -std=c++14 -D_GLIBCXX_USE_CXX11_ABI=0 -DUSE_GPU
```


## Optional Compilation Flags
-DUSE_BATCH: Enable batch inference
-DUSE_GPU: Use GPU for inference

## Run the Program
To run the program, use the following command:

`./silero aepyx.wav 16000 0.5`

The sample file aepyx.wav is part of the Voxconverse dataset.
File details: aepyx.wav is a 16kHz, 16-bit audio file.
