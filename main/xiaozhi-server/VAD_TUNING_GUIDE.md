# VAD Configuration Tuning Guide

## Quick Reference
Edit these values in `data/.config.yaml` under the `SileroVAD` section:

```yaml
SileroVAD:
  threshold: 0.5              # Voice detection sensitivity
  min_volume: 0.001          # Minimum volume level
  frame_window_threshold: 3   # Frames needed to confirm voice
  start_secs: 0.2            # Time to confirm voice started
  stop_secs: 0.8             # Time to confirm voice stopped
  min_silence_duration_ms: 1000  # Silence before ending sentence
```

## What Each Parameter Does

### 1. **threshold** (0.0 - 1.0)
- **What it does**: Minimum confidence score to detect voice
- **Current**: 0.5 (50% confidence needed)
- **Make it lower (0.3-0.4)**: More sensitive, detects quieter/unclear speech
- **Make it higher (0.6-0.7)**: Less sensitive, only clear speech detected
- **Effect**: Lower = more false positives, Higher = might miss soft speech

### 2. **min_volume** (0.0 - 1.0)
- **What it does**: Minimum audio volume to consider as voice
- **Current**: 0.001 (basically disabled)
- **Make it higher (0.01-0.05)**: Filters out background noise
- **Keep it low**: Detects whispers and quiet speech
- **Effect**: Higher = ignores quiet sounds, Lower = picks up everything

### 3. **frame_window_threshold** (1 - 10)
- **What it does**: How many consecutive frames must have voice to start detection
- **Current**: 3 frames
- **Make it lower (1-2)**: Faster response, but more false starts
- **Make it higher (4-6)**: More stable, but slower to react
- **Effect**: Lower = quicker but jumpier, Higher = smoother but delayed

### 4. **start_secs** (0.1 - 1.0)
- **What it does**: How long voice must be present before confirming "user is speaking"
- **Current**: 0.2 seconds
- **Make it lower (0.1)**: Super responsive, might trigger on short noises
- **Make it higher (0.3-0.5)**: More certain, but feels sluggish
- **Effect**: Lower = instant detection, Higher = fewer false starts

### 5. **stop_secs** (0.1 - 2.0)
- **What it does**: How long silence needed before confirming "user stopped speaking"
- **Current**: 0.8 seconds
- **Make it lower (0.5-0.6)**: Processes speech faster, might cut off pauses
- **Make it higher (1.0-1.5)**: Allows for natural pauses in speech
- **Effect**: Lower = quick processing but might split sentences, Higher = captures full thoughts

### 6. **min_silence_duration_ms** (500 - 3000)
- **What it does**: Milliseconds of silence before sending audio to ASR
- **Current**: 1000ms (1 second)
- **Make it lower (500-800)**: Faster response between sentences
- **Make it higher (1500-2000)**: Better for slow speakers or long pauses
- **Effect**: Lower = snappier conversation, Higher = more patient listening

## Common Scenarios

### For Noisy Environment
```yaml
threshold: 0.6              # Higher to avoid noise
min_volume: 0.05           # Filter out background sounds
frame_window_threshold: 5   # More frames for certainty
```

### For Quiet/Clear Environment
```yaml
threshold: 0.4              # More sensitive
min_volume: 0.001          # Detect whispers
frame_window_threshold: 2   # Quick response
```

### For Fast Conversation
```yaml
start_secs: 0.1            # Quick start
stop_secs: 0.5             # Quick stop
min_silence_duration_ms: 600  # Short pauses
```

### For Children/Slow Speakers
```yaml
start_secs: 0.3            # More time to start
stop_secs: 1.2             # Allow thinking pauses
min_silence_duration_ms: 1500  # Patient listening
```

## How to Test Changes

1. Edit `data/.config.yaml`
2. Restart the server
3. Watch the logs for:
   - "VAD state: SPEAKING" when you talk
   - "VAD state: QUIET" when you stop
   - "Voice stopped after Xms silence"

## Tips
- Start with small changes (±0.1 or ±100ms)
- Test with different speaking styles
- If getting cut off mid-sentence, increase `stop_secs` and `min_silence_duration_ms`
- If not detecting soft speech, decrease `threshold` and `min_volume`
- If too many false detections, increase `threshold` and `frame_window_threshold`