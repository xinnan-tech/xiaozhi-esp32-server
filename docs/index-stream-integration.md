# IndexStreamTTS Usage Guide

## 环境准备
### 1. 克隆项目 
```bash 
git clone https://github.com/Ksuriuri/index-tts-vllm.git
```
Enter the unzipped directory
```bash
cd index-tts-vllm
```
切换到指定版本 (使用VLLM-0.10.2的历史版本)
```bash
git checkout 224e8d5e5c8f66801845c66b30fa765328fd0be3
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
需要 pytorch 版本 2.8.0（对应 vllm 0.10.2），具体安装指令请参考：[pytorch 官网](https://pytorch.org/get-started/locally/)

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. 下载模型权重
### 方案一：下载官方权重文件后转换
此为官方权重文件，下载到本地任意路径即可，支持 IndexTTS-1.5 的权重  
| HuggingFace                                                   | ModelScope                                                          |
|---------------------------------------------------------------|---------------------------------------------------------------------|
| [IndexTTS](https://huggingface.co/IndexTeam/Index-TTS)        | [IndexTTS](https://modelscope.cn/models/IndexTeam/Index-TTS)        |
| [IndexTTS-1.5](https://huggingface.co/IndexTeam/IndexTTS-1.5) | [IndexTTS-1.5](https://modelscope.cn/models/IndexTeam/IndexTTS-1.5) |

下面以ModelScope的安装方法为例  
#### 请注意：git需要安装并初始化启用lfs（如已安装可以跳过）
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

#### 模型权重转换
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
如果显卡内存足够，可在脚本中添加启动参数 ----gpu_memory_utilization 来调整显存占用比例，默认值为 0.25

## 音色配置
index-tts-vllm支持通过配置文件注册自定义音色，支持单音色和混合音色配置。  
在项目根目录下的assets/speaker.json文件中配置自定义音色
### 配置格式说明
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
### 注意 （配置角色后需重启服务进行音色注册）
添加后需在智控台中添加相应的说话人（单模块则更换相应的voice）
