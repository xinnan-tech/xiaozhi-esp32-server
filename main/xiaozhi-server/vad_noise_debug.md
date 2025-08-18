# VAD Noise Detection Debug Guide

## Current Issue
The VAD (Voice Activity Detection) is picking up background noise and sending it to ASR, resulting in improper transcripts like "HE" when nothing was said.

## Current Settings (SileroVAD)
- threshold: 0.5
- threshold_low: 0.2
- min_silence_duration_ms: 1000
- frame_window_threshold: 3

## Recommendations to Reduce Noise Sensitivity

### 1. Increase VAD Thresholds
Edit `config.yaml` and try these settings:

```yaml
VAD:
  SileroVAD:
    type: silero
    threshold: 0.5  # Increased from 0.5
    threshold_low: 0.2  # Increased from 0.2
    model_dir: models/snakers4_silero-vad
    min_silence_duration_ms: 1000
    frame_window_threshold: 3  # Increased from 3
```

### 2. Alternative: Try TenVAD_ONNX with Higher Thresholds
```yaml
selected_module:
  VAD: TenVAD_ONNX  # Change from SileroVAD

VAD:
  TenVAD_ONNX:
    type: ten_vad_onnx
    model_path: models/ten-vad-onnx
    sample_rate: 16000
    hop_size: 256
    frame_size: 512
    threshold: 0.7  # Higher threshold for noisy environments
    threshold_low: 0.4  # Higher low threshold
    min_silence_duration_ms: 1000
    frame_window_threshold: 5  # More frames needed to confirm voice
```

### 3. Monitor Audio Files
The ASR logs are now saved in:
- CSV: `asr_logs/asr_log_YYYYMMDD.csv`
- JSON: `asr_logs/asr_log_YYYYMMDD.json`
- Text: `asr_logs/asr_log_YYYYMMDD.txt`

Check these logs to see:
- Audio length (now correctly calculated from WAV file)
- Transcript content
- File paths for manual inspection

### 4. Audio Length Fix
The audio length is now correctly calculated from the WAV file metadata instead of PCM data estimation.

### 5. Debug Information Added
- Number of audio chunks is now logged before processing
- Audio files are preserved (not deleted) for inspection