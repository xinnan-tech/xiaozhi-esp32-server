# Digital human startup method

## Overview

The test page integrates high-precision voice wake-up based on **Sherpa-ONNX**, supporting custom wake words and real-time detection. It uses a lightweight keyword spotting model for millisecond-level response times.

## Wake word model

### Model download (required)

**Important note**: The project does not include model files; download and configure them in advance.

### Official model download URL

- **Official model list**: <https://csukuangfj.github.io/sherpa/onnx/kws/pretrained_models/index.html>
- **Recommended model**: `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01`

### Download and configuration steps

#### 1. Download model package

```bash
# Method 1: Direct download (recommended)
cd main/digital-human/wakeword_runtime/
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2

# Unzip
tar xvf sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2

# Method 2: Use ModelScope
pip install modelscope
python -c "
from modelscope import snapshot_download
snapshot_download('pkufool/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01', cache_dir='./models')
"
```

#### 2. Configure model files

Model package contains the following files after download:

```
sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/
├── encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx    # Speed Priority
├── encoder-epoch-12-avg-2-chunk-16-left-64.onnx
├── encoder-epoch-99-avg-1-chunk-16-left-64.int8.onnx    # Speed Priority
├── encoder-epoch-99-avg-1-chunk-16-left-64.onnx         # Accuracy priority
├── decoder-epoch-12-avg-2-chunk-16-left-64.onnx
├── decoder-epoch-99-avg-1-chunk-16-left-64.onnx         # Accuracy priority
├── joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx     # Speed Priority
├── joiner-epoch-12-avg-2-chunk-16-left-64.onnx
├── joiner-epoch-99-avg-1-chunk-16-left-64.int8.onnx     # Speed Priority
├── joiner-epoch-99-avg-1-chunk-16-left-64.onnx          # Accuracy priority
├── tokens.txt                    # Token mapping table (required)
├── keywords_raw.txt              # Model package may include optional assets (runtime does not depend on them)
├── keywords.txt                  # Ready-made
├── test_wavs/                    # Test audio (optional)
├── configuration.json            # Model metadata (optional)
└── README.md                     # Documentation (optional)
```

#### 3. Select config scheme

**Option 1: Prioritize accuracy (recommended)**

```bash
cd sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01

# Create model directory
mkdir -p ../models

# Copy the accuracy-priority epoch-99 fp32 triplet
cp encoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/encoder.onnx
cp decoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/decoder.onnx
cp joiner-epoch-99-avg-1-chunk-16-left-64.onnx ../models/joiner.onnx

# Copy companion files
cp tokens.txt ../models/tokens.txt
# keywords_raw.txt can be kept if included in the model package; runtime does not depend on it
```

**Option 2: Speed priority**

```bash
cd sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01

# Create model directory
mkdir -p ../models

# Copy the speed-priority epoch-99 int8 triplet
cp encoder-epoch-99-avg-1-chunk-16-left-64.int8.onnx ../models/encoder.onnx
cp decoder-epoch-99-avg-1-chunk-16-left-64.onnx ../models/decoder.onnx
cp joiner-epoch-99-avg-1-chunk-16-left-64.int8.onnx ../models/joiner.onnx

# Copy companion files
cp tokens.txt ../models/tokens.txt
```

**Notes:

- **Do not mix fp32 and int8**: all three model files must use the same precision
- **Prefer epoch-99**: trained more thoroughly than epoch-12, with higher accuracy
- **Required Files**: `encoder.onnx` + `decoder.onnx` + `joiner.onnx` + `tokens.txt` + `keywords.txt`

### Final model file structure

After configuration, model files should be placed in the `wakeword_runtime/models/` directory. The full path is `main/digital-human/wakeword_runtime/models/`:

```
wakeword_runtime/models/
├── encoder.onnx      # Encoder model (after renaming)
├── decoder.onnx      # Decoder model (after renaming)
├── joiner.onnx       # Connector model (after rename)
├── tokens.txt        # Pinyin token mapping table (228-line version)
├── keywords.txt      # Keyword config file (auto-generated on first launch)
└── keywords_raw.txt  # Optional, runtime independent
```

## Startup method

Execute in `main/digital-human` directory:

```bash
pip install -r wakeword_runtime/requirements.txt
python start.py
```

Default address after startup:

- Page address: `http://127.0.0.1:8006/index.html`
- Event bridge address: `ws://127.0.0.1:8006/wakeword-ws`
- Health check: `http://127.0.0.1:8006/health`

Stop Method:

- Press `Ctrl+C` in the running terminal
- Simultaneously stops static page service, event bridge, and wake word detection process

## Config file description

The config file is located at [main/digital-human/wakeword_runtime/config.json](../main/digital-human/wakeword_runtime/config.json).

Current main configuration items:

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

Field descriptions:

| Parameter | Description |
| --- | --- |
| `wakeword.enabled` | Enable local wake word detection |
| `model_dir` | Directory containing the model and vocabulary |
| `audio.input_device` | Microphone input device, defaults to system default device |
| `audio.sample_rate` | Sample rate, default `16000` |
| `audio.channels` | Number of channels, default `1` |
| `detector.num_threads` | Detector thread count |
| `detector.provider` | Inference provider, currently usually `cpu` |
| `detector.max_active_paths` | Search path count |
| `detector.keywords_score` | Keyword enhancement score |
| `detector.keywords_threshold` | Detection threshold |
| `detector.num_trailing_blanks` | Trailing whitespace count |
| `detector.cooldown_seconds` | Continuous trigger cooldown time |
| `logging.level` | Log level |
| `logging.dir` | Log directory |
| `logging.file` | Log file name |

## Recommended workflow

### First Use

1. Prepare model files and `tokens.txt` in the `models/` directory
2. Verify `models/keywords.txt` exists
3. Run `python start.py` in the `digital-human` directory
4. Open `http://127.0.0.1:8006/index.html` in the browser
5. Go to the settings page and check the "wake word" config

### Modify Wake Word

1. Open digital human page settings
2. Switch to "Wake Word" tab
3. Modify enabled status or wake word list
4. Click " to apply the wake word"
5. Decide whether to restart immediately based on prompt

### Disable wake word

1. Change "Enable local wake word" to disabled
2. Click " to apply the wake word"
3. Recommend immediate restart

When disabled:

- Page and event bridge remain available
- Wake word detection will not continue running
