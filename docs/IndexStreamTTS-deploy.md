# IndexStreamTTS 使用指南

## 环境准备
### 1. 克隆项目 （这里使用的为VLLM的版本）
```bash 
git clone https://github.com/Ksuriuri/index-tts-vllm.git
cd index-tts-vllm
```

### 2. 创建并激活 conda 环境
```bash 
conda create -n index-tts-vllm python=3.12
conda activate index-tts-vllm
```

### 3. 安装PyTorch
#### 查看显卡最高支持的版本和实际安装的版本
```bash
nvidia-smi
nvcc --version
``` 
#### 驱动支持的最高 CUDA 版本
```bash
CUDA Version: 12.8
```
#### 实际安装的 CUDA 编译器版本
```bash
Cuda compilation tools, release 12.8, V12.8.89
```
#### 那么对应的安装命令 (请注意不要横跨大版本！！！)
```bash
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
```
优先建议安装 pytorch 2.7.0（对应 vllm 0.9.0），具体安装指令请参考：[pytorch 官网](https://pytorch.org/get-started/locally/]\)  
若显卡不支持，请安装 pytorch 2.5.1（对应 vllm 0.7.3），并将 requirements.txt 中 vllm==0.9.0 修改为 vllm==0.7.3

### 4. 安装依赖
```bash 
pip install -r requirements.txt
```

### 5. 下载模型权重
此为官方权重文件，下载到本地任意路径即可，支持 IndexTTS-1.5 的权重  
| HuggingFace                                                   | ModelScope                                                          |
|---------------------------------------------------------------|---------------------------------------------------------------------|
| [IndexTTS](https://huggingface.co/IndexTeam/Index-TTS)        | [IndexTTS](https://modelscope.cn/models/IndexTeam/Index-TTS)        |
| [IndexTTS-1.5](https://huggingface.co/IndexTeam/IndexTTS-1.5) | [IndexTTS-1.5](https://modelscope.cn/models/IndexTeam/IndexTTS-1.5) |

下面以ModelScope的安装方法为例  
### 请注意：git需要安装并初始化启用lfs（如已安装可以跳过）
```bash
sudo apt-get install git-lfs
git lfs install
```
创建模型目录，并拉取模型
```bash 
mkkdir model_dir
cd model_dir
git clone https://www.modelscope.cn/IndexTeam/IndexTTS-1.5.git
```

### 5. 模型权重转换
```bash 
bash convert_hf_format.sh /path/to/your/model_dir
```
例如：你下载的IndexTTS-1.5模型存放在model_dir目录下，则执行以下命令
```bash
bash convert_hf_format.sh model_dir/IndexTTS-1.5
```
此操作会将官方的模型权重转换为 transformers 库兼容的版本，保存在模型权重路径下的 vllm 文件夹中，方便后续 vllm 库加载模型权重

### 6. 更改接口适配一下项目
接口返回数据与项目不适配需要调整一下，使其直接返回音频数据
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

### 7.编写sh启动脚本（请注意要在相应的conda环境下运行）
```bash 
vi start_api.sh
```
### 将下面内容粘贴进去并按:输入wq保存  
#### 脚本中的/home/system/indexTTS/index-tts-vllm/model_dir/IndexTTS-1.5 请自行修改为实际路径
```bash
# 激活conda环境
conda activate index-tts-vllm 
echo "激活项目conda环境"
sleep 2
# 查找占用11996端口的进程号
PID_VLLM=$(sudo netstat -tulnp | grep 11996 | awk '{print $7}' | cut -d'/' -f1)

# 检查是否找到进程号
if [ -z "$PID_VLLM" ]; then
  echo "没有找到占用11996端口的进程"
else
  echo "找到占用11996端口的进程，进程号为: $PID_VLLM"
  # 先尝试普通kill，等待2秒
  kill $PID_VLLM
  sleep 2
  # 检查进程是否还在
  if ps -p $PID_VLLM > /dev/null; then
    echo "进程仍在运行，强制终止..."
    kill -9 $PID_VLLM
  fi
  echo "已终止进程 $PID_VLLM"
fi

# 创建tmp目录（如果不存在）
mkdir -p tmp

# 后台运行api_server.py，日志重定向到tmp/server.log
export VLLM_USE_V1=0
nohup python api_server.py --model_dir /home/system/indexTTS/index-tts-vllm/model_dir/IndexTTS-1.5 --port 11996 > tmp/server.log 2>&1 &
echo "api_server.py 已在后台运行，日志请查看 tmp/server.log"
```
给脚本执行权限并运行脚本
```bash 
chmod +x tmp
./start_api.sh
```
日志会在tmp/server.log中输出，可以通过以下命令查看日志情况
```bash
tail -f tmp/server.log
```
## 音色配置
index-tts-vllm支持通过配置文件注册自定义音色，支持单音色和混合音色配置。  
在项目根目录下的assets/speaker.json文件中配置自定义音色  
### 配置格式说明
```bash
{
    "说话人名称1": [
        "音频文件路径1.wav",
        "音频文件路径2.wav"
    ],
    "说话人名称2": [
        "音频文件路径3.wav"
    ]
}
```
### 注意
添加后需在智控台中添加相应的说话人（单模块则更换相应的voice）