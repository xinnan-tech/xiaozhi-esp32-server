from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import torch
torch.set_num_threads(1)

def test_jit_model():
    model = load_silero_vad(onnx=False)
    for path in ["tests/data/test.wav", "tests/data/test.opus", "tests/data/test.mp3"]:
        audio = read_audio(path, sampling_rate=16000)
        speech_timestamps = get_speech_timestamps(audio, model, visualize_probs=False, return_seconds=True)
        assert speech_timestamps is not None
        out = model.audio_forward(audio, sr=16000)
        assert out is not None

def test_onnx_model():
    model = load_silero_vad(onnx=True)
    for path in ["tests/data/test.wav", "tests/data/test.opus", "tests/data/test.mp3"]:
        audio = read_audio(path, sampling_rate=16000)
        speech_timestamps = get_speech_timestamps(audio, model, visualize_probs=False, return_seconds=True)
        assert speech_timestamps is not None

        out = model.audio_forward(audio, sr=16000)
        assert out is not None
