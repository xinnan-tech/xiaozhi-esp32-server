# Stream example in C++

Here's a simple example of the vad model in c++ onnxruntime.



## Requirements

Code are tested in the environments bellow, feel free to try others.

- WSL2 + Debian-bullseye (docker)  
- gcc 12.2.0
- onnxruntime-linux-x64-1.12.1



## Usage

1. Install gcc 12.2.0, or just pull the docker image with `docker pull gcc:12.2.0-bullseye`

2. Install onnxruntime-linux-x64-1.12.1

   - Download lib onnxruntime: 

     `wget https://github.com/microsoft/onnxruntime/releases/download/v1.12.1/onnxruntime-linux-x64-1.12.1.tgz`

   - Unzip. Assume the path is `/root/onnxruntime-linux-x64-1.12.1`

3. Modify wav path & Test configs in main function

   `wav::WavReader wav_reader("${path_to_your_wav_file}");`

   test sample rate, frame per ms, threshold...

4. Build with gcc and run

   ```bash
   # Build
   g++ silero-vad-onnx.cpp -I /root/onnxruntime-linux-x64-1.12.1/include/ -L /root/onnxruntime-linux-x64-1.12.1/lib/ -lonnxruntime  -Wl,-rpath,/root/onnxruntime-linux-x64-1.12.1/lib/ -o test
   
   # Run
   ./test
   ```