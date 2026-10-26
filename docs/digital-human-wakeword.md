# 数字人digital-human启动方法

## 概述

测试页面集成了基于 **Sherpa-ONNX** 的高精度语音唤醒功能，支持自定义唤醒词和实时检测。使用轻量级关键词检测模型，提供毫秒级响应速度。

## 唤醒词模型

### 模型下载（必需）

**重要说明**: 项目不包含模型文件，需要提前下载配置。

### 官方模型下载地址

- **官方模型列表**: <https://csukuangfj.github.io/sherpa/onnx/kws/pretrained_models/index.html>
- **推荐模型**: `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01`

### 下载和配置步骤

#### 1. 下载模型包

```bash
# 方法1：直接下载（推荐）
cd main/digital-human/wakeword_runtime/
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2

# 解压
tar xvf sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2

# 方法2：使用ModelScope
# 这份仓库里只有 epoch-12 的模型，文件名里的 avg 是 avg-2，不是 avg-1
# 照抄下面「配置模型文件」的命令时，把 epoch-99-avg-1 换成 epoch-12-avg-2（avg 一起换，只换 epoch 数字会找不到文件）
# 方法2 的前提是仓库里有 epoch-12 的 encoder 和 joiner 两份 .int8.onnx（速度优先那套要用），
# 哪天仓库里缺了这两份 int8，方法2 就用不了，只能改用方法1
pip install modelscope
python -c "
from modelscope import snapshot_download
snapshot_download('pkufool/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01', local_dir='./sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01')
"
```

运行时只认 `models/` 目录下的四个固定文件名（`encoder.onnx`、`decoder.onnx`、`joiner.onnx`、`tokens.txt`），也不搜子目录。文件留在下载目录里不做拷贝改名，启动会报 `No valid model directory found`。两种方法下载完都要接着做下面「配置模型文件」那节的拷贝改名。

#### 2. 配置模型文件

模型包下载后包含以下文件：

```
sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/
├── encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx    # 速度优先
├── encoder-epoch-12-avg-2-chunk-16-left-64.onnx
├── encoder-epoch-99-avg-1-chunk-16-left-64.int8.onnx    # 速度优先
├── encoder-epoch-99-avg-1-chunk-16-left-64.onnx         # 精度优先
├── decoder-epoch-12-avg-2-chunk-16-left-64.onnx
├── decoder-epoch-99-avg-1-chunk-16-left-64.onnx         # 精度优先
├── joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx     # 速度优先
├── joiner-epoch-12-avg-2-chunk-16-left-64.onnx
├── joiner-epoch-99-avg-1-chunk-16-left-64.int8.onnx     # 速度优先
├── joiner-epoch-99-avg-1-chunk-16-left-64.onnx          # 精度优先
├── tokens.txt                    # Token映射表（必需）
├── keywords_raw.txt              # 模型包里可能附带（可选，runtime 不依赖）
├── keywords.txt                  # 现成的
├── test_wavs/                    # 测试音频（可选）
├── configuration.json            # 模型元信息（可选）
└── README.md                     # 说明文档（可选）
```

#### 3. 选择配置方案

**方案一：精度优先（推荐）**

```bash
cd sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01

# 创建模型目录
mkdir -p ../models

# 复制精度优先的epoch-99 fp32三件套
cp encoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/encoder.onnx
cp decoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/decoder.onnx
cp joiner-epoch-99-avg-1-chunk-16-left-64.onnx ../models/joiner.onnx

# 复制配套文件
cp tokens.txt ../models/tokens.txt
# keywords_raw.txt 如果模型包里附带，可自行保留；runtime 不依赖它
```

**方案二：速度优先**

```bash
cd sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01

# 创建模型目录
mkdir -p ../models

# 复制速度优先的epoch-99 三件套：encoder 和 joiner 用 int8，decoder 只有 fp32 一版
cp encoder-epoch-99-avg-1-chunk-16-left-64.int8.onnx ../models/encoder.onnx
cp decoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/decoder.onnx
cp joiner-epoch-99-avg-1-chunk-16-left-64.int8.onnx ../models/joiner.onnx

# 复制配套文件
cp tokens.txt ../models/tokens.txt
```

**注意事项**:

- **精度怎么选**：encoder 和 joiner 有 int8 和 fp32 两版，decoder 只有 fp32 一版（官方包里没有 int8 的 decoder），别去凑 int8 的 decoder
- **优先选择 epoch-99**：比 epoch-12 训练更充分，精度更高
- **必需文件**：`encoder.onnx` + `decoder.onnx` + `joiner.onnx` + `tokens.txt` 四个，`keywords.txt` 不在其中，它不用自己准备，首次启动会用配置里的唤醒词自动生成

### 最终模型文件结构

配置完成后，模型文件应放在 `wakeword_runtime/models/` 目录下，完整路径为 `main/digital-human/wakeword_runtime/models/`：

```
wakeword_runtime/models/
├── encoder.onnx      # 编码器模型（重命名后）
├── decoder.onnx      # 解码器模型（重命名后）
├── joiner.onnx       # 连接器模型（重命名后）
├── tokens.txt        # 拼音 Token 映射表（228行版本）
├── keywords.txt      # 关键词配置文件（首次启动自动生成）
└── keywords_raw.txt  # 可选，runtime 不依赖
```

## 启动方式

在 `main/digital-human` 目录执行：

```bash
pip install -r wakeword_runtime/requirements.txt
python start.py
```

启动后默认地址：

- 页面地址：`http://127.0.0.1:8006/index.html`
- 事件桥地址：`ws://127.0.0.1:8006/wakeword-ws`
- 健康检查：`http://127.0.0.1:8006/health`

停止方式：

- 在运行终端按 `Ctrl+C`
- 会同时停止静态页面服务、事件桥和唤醒词检测流程

## 配置文件说明

配置文件位于 [main/digital-human/wakeword_runtime/config.json](../main/digital-human/wakeword_runtime/config.json)。

当前主要配置项：

```json
{
  "wakeword": {
    "enabled": true
  },
  "model_dir": "models",
  "audio": {
    "input_device": null,
    "sample_rate": 16000,
    "channels": 1
  },
  "detector": {
    "num_threads": 4,
    "provider": "cpu",
    "max_active_paths": 2,
    "keywords_score": 1.8,
    "keywords_threshold": 0.1,
    "num_trailing_blanks": 1,
    "cooldown_seconds": 1.5
  },
  "logging": {
    "level": "INFO",
    "dir": "logs",
    "file": "wakeword-runtime.log"
  }
}
```

各字段含义：

| 参数 | 说明 |
| --- | --- |
| `wakeword.enabled` | 是否启用本地唤醒词检测 |
| `model_dir` | 模型和词表所在目录 |
| `audio.input_device` | 麦克风输入设备，默认使用系统默认设备 |
| `audio.sample_rate` | 采样率，默认 `16000` |
| `audio.channels` | 声道数，默认 `1` |
| `detector.num_threads` | 检测器线程数 |
| `detector.provider` | 推理 provider，当前通常为 `cpu` |
| `detector.max_active_paths` | 搜索路径数 |
| `detector.keywords_score` | 关键词增强分数 |
| `detector.keywords_threshold` | 检测阈值 |
| `detector.num_trailing_blanks` | 尾随空白数量 |
| `detector.cooldown_seconds` | 连续触发冷却时间 |
| `logging.level` | 日志等级 |
| `logging.dir` | 日志目录 |
| `logging.file` | 日志文件名 |

## 推荐使用流程

### 首次使用

1. 先按上面「模型下载（必需）」那节把模型包下载解压，再按「配置模型文件」那节把模型放到 `models/` 目录，该目录下要有 `encoder.onnx`、`decoder.onnx`、`joiner.onnx` 和 `tokens.txt` 四个文件
2. `models/keywords.txt` 不用自己准备，首次启动会用配置里的唤醒词自动生成
3. 在 `digital-human` 目录运行 `python start.py`
4. 浏览器打开 `http://127.0.0.1:8006/index.html`
5. 进入设置页检查“唤醒词”配置

模型没放到位就启动，只会打印「警告: 唤醒词服务启动失败」：页面能打开，麦克风的输入流也已经打开，但没有唤醒词检测在消费这些数据，语音唤不醒。

### 修改唤醒词

1. 打开数字人页面设置
2. 切到“唤醒词”页签
3. 修改启用状态或唤醒词列表
4. 点击“应用唤醒词”
5. 根据提示决定是否立即重启

### 禁用唤醒词

1. 将“启用本地唤醒词”改成禁用
2. 点击“应用唤醒词”
3. 建议立即重启一次

禁用后：

- 页面与事件桥仍然可用
- 唤醒词检测不会继续运行
