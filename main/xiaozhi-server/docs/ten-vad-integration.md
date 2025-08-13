# TEN VAD Integration Guide

This guide explains how to integrate and use TEN VAD (Voice Activity Detection) in the XiaoZhi ESP32 Server.

## Overview

TEN VAD is a high-performance voice activity detection system that can be used as an alternative to Silero VAD. It provides accurate voice detection with configurable thresholds and parameters.

## Installation

### Method 1: Automatic Installation (Recommended)

Run the installation script:

```bash
cd main/xiaozhi-server
python scripts/install_ten_vad.py
```

### Method 2: Manual Installation

1. Install the TEN VAD package:
```bash
pip install ten-vad
```

2. Create the model directory:
```bash
mkdir -p models/ten-vad
```

3. The model files will be downloaded automatically on first use.

## Configuration

The TEN VAD configuration is already added to your `.config.yaml` file:

```yaml
VAD:
  TenVAD:
    type: ten_vad
    model_path: models/ten-vad
    sample_rate: 16000
    frame_size: 512
    threshold: 0.5
    threshold_low: 0.2
    min_silence_duration_ms: 1000
    frame_window_threshold: 3
```

### Configuration Parameters

- `model_path`: Path to the TEN VAD model files
- `sample_rate`: Audio sample rate (default: 16000 Hz)
- `frame_size`: Audio frame size for processing (default: 512 samples)
- `threshold`: High threshold for voice detection (0.0-1.0)
- `threshold_low`: Low threshold for voice detection (0.0-1.0)
- `min_silence_duration_ms`: Minimum silence duration to consider speech ended
- `frame_window_threshold`: Number of positive frames needed to detect voice

## Usage

To use TEN VAD, update your configuration:

```yaml
selected_module:
  VAD: TenVAD  # Change from SileroVAD to TenVAD
```

## Performance Tuning

### Sensitivity Adjustment

- **More Sensitive**: Lower `threshold` and `threshold_low` values
- **Less Sensitive**: Higher `threshold` and `threshold_low` values

### Responsiveness

- **Faster Response**: Lower `frame_window_threshold` value
- **More Stable**: Higher `frame_window_threshold` value

### End-of-Speech Detection

- **Quicker Cutoff**: Lower `min_silence_duration_ms`
- **More Patient**: Higher `min_silence_duration_ms`

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `ten-vad` package is installed
   ```bash
   pip install ten-vad
   ```

2. **Model Loading Error**: Ensure the model path exists and is accessible
   ```bash
   ls -la models/ten-vad/
   ```

3. **Performance Issues**: Try adjusting `frame_size` or `sample_rate`

### Debug Logging

Enable debug logging to see TEN VAD detection results:

```yaml
log:
  log_level: DEBUG
```

This will show periodic VAD detection results in the logs.

## Comparison with Other VAD Systems

| Feature | TEN VAD | Silero VAD | 
|---------|---------|------------|
| Accuracy | High | High |
| Speed | Fast | Fast |
| Memory Usage | Medium | Low |
| Model Size | Medium | Small |
| Language Support | Multi | Multi |

## Advanced Configuration

### Custom Model Path

If you have a custom TEN VAD model:

```yaml
VAD:
  TenVAD:
    model_path: /path/to/your/custom/model
```

### Multiple Configurations

You can define multiple TEN VAD configurations:

```yaml
VAD:
  TenVAD_Sensitive:
    type: ten_vad
    threshold: 0.3
    threshold_low: 0.1
    
  TenVAD_Conservative:
    type: ten_vad
    threshold: 0.7
    threshold_low: 0.4
```

## Support

For issues specific to TEN VAD integration:
1. Check the logs for error messages
2. Verify the installation using the installation script
3. Test with different threshold values
4. Refer to the TEN VAD documentation: https://github.com/ten-framework/ten-vad

For general XiaoZhi ESP32 Server issues, refer to the main documentation.