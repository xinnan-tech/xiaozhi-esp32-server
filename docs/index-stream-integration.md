# IndexStreamTTS Usage Guide

## Environment Preparation
### 1. Clone the project (note that the release version of VLLM1.0 is used here)
```bash 
https://github.com/Ksuriuri/index-tts-vllm/releases/tag/IndexTTS-vLLM-1.0
```
Enter the unzipped directory
```bash
cd index-tts-vllm
```

### 2. Create and activate a conda environment
```bash
conda create -n index-tts-vllm python=3.12
conda activate index-tts-vllm
```

### 3. Install PyTorch. Version 2.8.0 (latest version) is required.
#### Check the highest supported version of the graphics card and the actual installed version
```bash
nvidia-smi
nvcc --version
``` 
#### Highest CUDA version supported by the driver
```bash
CUDA Version: 12.8
```
#### Actual installed CUDA compiler version
```bash
Cuda compilation tools, release 12.8, V12.8.89
```
#### Then the corresponding installation command (pytorch defaults to the 12.8 driver version)
```bash
pip install torch torchvision
```
You need PyTorch version 2.8.0 (corresponding to VLLM 0.10.2). For specific installation instructions, please refer to the [PyTorch official website](https://pytorch.org/get-started/locally/)  

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Download model weights
This is the official weight file, which can be downloaded to any local path. It supports the weight of IndexTTS-1.5.  
| HuggingFace                                                   | ModelScope                                                          |
|---------------------------------------------------------------|---------------------------------------------------------------------|
| [IndexTTS](https://huggingface.co/IndexTeam/Index-TTS)        | [IndexTTS](https://modelscope.cn/models/IndexTeam/Index-TTS)        |
| [IndexTTS-1.5](https://huggingface.co/IndexTeam/IndexTTS-1.5) | [IndexTTS-1.5](https://modelscope.cn/models/IndexTeam/IndexTTS-1.5) |

The following is an example of how to install ModelScope  
### Please note: Git needs to be installed and initialized to enable LFS (if already installed, you can skip this step)
```bash
sudo apt-get install git-lfs
git lfs install
```
Create a model directory and pull the model
```bash
mkdir model_dir
cd model_dir
git clone https://www.modelscope.cn/IndexTeam/IndexTTS-1.5.git
```

### 5. Model weight conversion
```bash
bash convert_hf_format.sh /path/to/your/model_dir
```
For example, if the IndexTTS-1.5 model you downloaded is stored in the model_dir directory, execute the following command:
```bash
bash convert_hf_format.sh model_dir/IndexTTS-1.5
```
This operation will convert the official model weights into a version compatible with the transformers library and save it in the vllm folder under the model weight path, making it easier to load the model weights in the vllm library later.

### 6. Change the interface to adapt to the project
The data returned by the interface is not compatible with the project and needs to be adjusted to return the audio data directly.
```bash
we api_server.py
```
```bash
@app.post("/tts", responses={
    200: {"content": {"application/octet-stream": {}}},
    500: {"content": {"application/json": {}}}
})
async def tts_api(request: Request):
    try:
        data = await request.json()
        text = data["text"]
        character = data["character"]

        global tts
        sr, wav = await tts.infer_with_ref_audio_embed(character, text)

        return Response(content=wav.tobytes(), media_type="application/octet-stream")
        
    except Exception as ex:
        tb_str = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        print(tb_str)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(tb_str)
            }
        )
```

### 7. Write the sh startup script (please note that it must be run in the corresponding conda environment)
```bash
we start_api.sh
```
### Paste the following content and press: Enter wq to save  
#### Please modify the /home/system/index-tts-vllm/model_dir/IndexTTS-1.5 in the script to the actual path
```bash
# Activate the conda environment
conda activate index-tts-vllm 
echo "Activate project conda environment"
sleep 2
# Find the process number occupying port 11996
PID_VLLM=$(sudo netstat -tulnp | grep 11996 | awk '{print $7}' | cut -d'/' -f1)

# Check if the process ID is found
if [ -z "$PID_VLLM" ]; then
  echo "No process occupying port 11996 was found"
else
  echo "Found the process occupying port 11996, process ID: $PID_VLLM"
  # Try a normal kill first, wait 2 seconds
  kill $PID_VLLM
  sleep 2
  # Check if the process is still alive
  if ps -p $PID_VLLM > /dev/null; then
    echo "The process is still running, force terminate..."
    kill -9 $PID_VLLM
  be
  echo "Process $PID_VLLM has been terminated"
be

# Find the process occupying VLLM::EngineCore
GPU_PIDS=$(ps aux | grep -E "VLLM|EngineCore" | grep -v grep | awk '{print $2}')

# Check if the process ID is found
if [ -z "$GPU_PIDS" ]; then
  echo "No VLLM related process found"
else
  echo "Found VLLM related process, process ID: $GPU_PIDS"
  # Try a normal kill first, wait 2 seconds
  kill $GPU_PIDS
  sleep 2
  # Check if the process is still alive
  if ps -p $GPU_PIDS > /dev/null; then
    echo "The process is still running, force terminate..."
    kill -9 $GPU_PIDS
  be
  echo "Process $GPU_PIDS has been terminated"
be

# Create the tmp directory (if it does not exist)
mkdir -p tmp

# Run api_server.py in the background and redirect the log to tmp/server.log
nohup python api_server.py --model_dir /home/system/index-tts-vllm/model_dir/IndexTTS-1.5 --port 11996 > tmp/server.log 2>&1 &
echo "api_server.py is running in the background. Please check tmp/server.log for the logs."
```
Give the script execute permission and run the script
```bash 
chmod +x start_api.sh
./start_api.sh
```
The log will be output in tmp/server.log. You can view the log status by the following command
```bash
tail -f tmp/server.log
```
## Tone Configuration
index-tts-vllm supports registering custom timbres through configuration files, and supports single-timbre and mixed-timbre configurations.  
Configure custom timbre in the assets/speaker.json file in the project root directory
### Configuration format description
```bash
{
    "Speaker Name 1": [
        "Audio file path 1.wav",
        "Audio file path 2.wav"
    ],
    "Speaker Name 2": [
        "Audio file path 3.wav"
    ]
}
```
### Note (need to restart the service to register)
After adding, you need to add the corresponding speaker in the smart console (for single module, change the corresponding voice)
