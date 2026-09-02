import torch
import torchaudio
from typing import Callable, List
import warnings
from packaging import version

languages = ['ru', 'en', 'de', 'es']


class OnnxWrapper():

    def __init__(self, path, force_onnx_cpu=False):
        import numpy as np
        global np
        import onnxruntime

        opts = onnxruntime.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1

        if force_onnx_cpu and 'CPUExecutionProvider' in onnxruntime.get_available_providers():
            self.session = onnxruntime.InferenceSession(path, providers=['CPUExecutionProvider'], sess_options=opts)
        else:
            self.session = onnxruntime.InferenceSession(path, sess_options=opts)

        self.reset_states()
        if '16k' in path:
            warnings.warn('This model support only 16000 sampling rate!')
            self.sample_rates = [16000]
        else:
            self.sample_rates = [8000, 16000]

    def _validate_input(self, x, sr: int):
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if x.dim() > 2:
            raise ValueError(f"Too many dimensions for input audio chunk {x.dim()}")

        if sr != 16000 and (sr % 16000 == 0):
            step = sr // 16000
            x = x[:,::step]
            sr = 16000

        if sr not in self.sample_rates:
            raise ValueError(f"Supported sampling rates: {self.sample_rates} (or multiply of 16000)")
        if sr / x.shape[1] > 31.25:
            raise ValueError("Input audio chunk is too short")

        return x, sr

    def reset_states(self, batch_size=1):
        self._state = torch.zeros((2, batch_size, 128)).float()
        self._context = torch.zeros(0)
        self._last_sr = 0
        self._last_batch_size = 0

    def __call__(self, x, sr: int):

        x, sr = self._validate_input(x, sr)
        num_samples = 512 if sr == 16000 else 256

        if x.shape[-1] != num_samples:
            raise ValueError(f"Provided number of samples is {x.shape[-1]} (Supported values: 256 for 8000 sample rate, 512 for 16000)")

        batch_size = x.shape[0]
        context_size = 64 if sr == 16000 else 32

        if not self._last_batch_size:
            self.reset_states(batch_size)
        if (self._last_sr) and (self._last_sr != sr):
            self.reset_states(batch_size)
        if (self._last_batch_size) and (self._last_batch_size != batch_size):
            self.reset_states(batch_size)

        if not len(self._context):
            self._context = torch.zeros(batch_size, context_size)

        x = torch.cat([self._context, x], dim=1)
        if sr in [8000, 16000]:
            ort_inputs = {'input': x.numpy(), 'state': self._state.numpy(), 'sr': np.array(sr, dtype='int64')}
            ort_outs = self.session.run(None, ort_inputs)
            out, state = ort_outs
            self._state = torch.from_numpy(state)
        else:
            raise ValueError()

        self._context = x[..., -context_size:]
        self._last_sr = sr
        self._last_batch_size = batch_size

        out = torch.from_numpy(out)
        return out

    def audio_forward(self, x, sr: int):
        outs = []
        x, sr = self._validate_input(x, sr)
        self.reset_states()
        num_samples = 512 if sr == 16000 else 256

        if x.shape[1] % num_samples:
            pad_num = num_samples - (x.shape[1] % num_samples)
            x = torch.nn.functional.pad(x, (0, pad_num), 'constant', value=0.0)

        for i in range(0, x.shape[1], num_samples):
            wavs_batch = x[:, i:i+num_samples]
            out_chunk = self.__call__(wavs_batch, sr)
            outs.append(out_chunk)

        stacked = torch.cat(outs, dim=1)
        return stacked.cpu()


class Validator():
    def __init__(self, url, force_onnx_cpu):
        self.onnx = True if url.endswith('.onnx') else False
        torch.hub.download_url_to_file(url, 'inf.model')
        if self.onnx:
            import onnxruntime
            if force_onnx_cpu and 'CPUExecutionProvider' in onnxruntime.get_available_providers():
                self.model = onnxruntime.InferenceSession('inf.model', providers=['CPUExecutionProvider'])
            else:
                self.model = onnxruntime.InferenceSession('inf.model')
        else:
            self.model = init_jit_model(model_path='inf.model')

    def __call__(self, inputs: torch.Tensor):
        with torch.no_grad():
            if self.onnx:
                ort_inputs = {'input': inputs.cpu().numpy()}
                outs = self.model.run(None, ort_inputs)
                outs = [torch.Tensor(x) for x in outs]
            else:
                outs = self.model(inputs)

        return outs


def read_audio(path: str, sampling_rate: int = 16000) -> torch.Tensor:
    ta_ver = version.parse(torchaudio.__version__)
    if ta_ver < version.parse("2.9"):
        try:
            effects = [['channels', '1'],['rate', str(sampling_rate)]]
            wav, sr = torchaudio.sox_effects.apply_effects_file(path, effects=effects)
        except:
            wav, sr = torchaudio.load(path)
    else:
        try:
            wav, sr = torchaudio.load(path)
        except:
            try:
                from torchcodec.decoders import AudioDecoder
                samples = AudioDecoder(path).get_all_samples()
                wav = samples.data
                sr = samples.sample_rate
            except ImportError:
                raise RuntimeError(
                    f"torchaudio version {torchaudio.__version__} requires torchcodec for audio I/O. "
                    + "Install torchcodec or pin torchaudio < 2.9"
                )

    if wav.ndim > 1 and wav.size(0) > 1:
        wav = wav.mean(dim=0, keepdim=True)

    if sr != sampling_rate:
        wav = torchaudio.transforms.Resample(sr, sampling_rate)(wav)

    return wav.squeeze(0)


def save_audio(path: str, tensor: torch.Tensor, sampling_rate: int = 16000):
    tensor = tensor.detach().cpu()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)

    ta_ver = version.parse(torchaudio.__version__)

    try:
        torchaudio.save(path, tensor, sampling_rate, bits_per_sample=16)
    except Exception:
        if ta_ver >= version.parse("2.9"):
            try:
                from torchcodec.encoders import AudioEncoder
                encoder = AudioEncoder(tensor, sample_rate=16000)
                encoder.to_file(path)
            except ImportError:
                raise RuntimeError(
                    f"torchaudio version {torchaudio.__version__} requires torchcodec for saving. "
                    + "Install torchcodec or pin torchaudio < 2.9"
                )
        else:
            raise


def init_jit_model(model_path: str,
                   device=torch.device('cpu')):
    model = torch.jit.load(model_path, map_location=device)
    model.eval()
    return model


def make_visualization(probs, step):
    import pandas as pd
    pd.DataFrame({'probs': probs},
                 index=[x * step for x in range(len(probs))]).plot(figsize=(16, 8),
                 kind='area', ylim=[0, 1.05], xlim=[0, len(probs) * step],
                 xlabel='seconds',
                 ylabel='speech probability',
                 colormap='tab20')


@torch.no_grad()
def get_speech_timestamps(audio: torch.Tensor,
                          model,
                          threshold: float = 0.5,
                          sampling_rate: int = 16000,
                          min_speech_duration_ms: int = 250,
                          max_speech_duration_s: float = float('inf'),
                          min_silence_duration_ms: int = 100,
                          speech_pad_ms: int = 30,
                          return_seconds: bool = False,
                          time_resolution: int = 1,
                          visualize_probs: bool = False,
                          progress_tracking_callback: Callable[[float], None] = None,
                          neg_threshold: float = None,
                          window_size_samples: int = 512,
                          min_silence_at_max_speech: int = 98,
                          use_max_poss_sil_at_max_speech: bool = True):

    """
    This method is used for splitting long audios into speech chunks using silero VAD

    Parameters
    ----------
    audio: torch.Tensor, one dimensional
        One dimensional float torch.Tensor, other types are casted to torch if possible

    model: preloaded .jit/.onnx silero VAD model

    threshold: float (default - 0.5)
        Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, probabilities ABOVE this value are considered as SPEECH.
        It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

    sampling_rate: int (default - 16000)
        Currently silero VAD models support 8000 and 16000 (or multiply of 16000) sample rates

    min_speech_duration_ms: int (default - 250 milliseconds)
        Final speech chunks shorter min_speech_duration_ms are thrown out

    max_speech_duration_s: int (default -  inf)
        Maximum duration of speech chunks in seconds
        Chunks longer than max_speech_duration_s will be split at the timestamp of the last silence that lasts more than 100ms (if any), to prevent aggressive cutting.
        Otherwise, they will be split aggressively just before max_speech_duration_s.

    min_silence_duration_ms: int (default - 100 milliseconds)
        In the end of each speech chunk wait for min_silence_duration_ms before separating it

    speech_pad_ms: int (default - 30 milliseconds)
        Final speech chunks are padded by speech_pad_ms each side

    return_seconds: bool (default - False)
        whether return timestamps in seconds (default - samples)

    time_resolution: bool (default - 1)
        time resolution of speech coordinates when requested as seconds

    visualize_probs: bool (default - False)
        whether draw prob hist or not

    progress_tracking_callback: Callable[[float], None] (default - None)
        callback function taking progress in percents as an argument

    neg_threshold: float (default = threshold - 0.15)
        Negative threshold (noise or exit threshold). If model's current state is SPEECH, values BELOW this value are considered as NON-SPEECH.

    min_silence_at_max_speech: int (default - 98ms)
        Minimum silence duration in ms which is used to avoid abrupt cuts when max_speech_duration_s is reached

    use_max_poss_sil_at_max_speech: bool (default - True)
        Whether to use the maximum possible silence at max_speech_duration_s or not. If not, the last silence is used.

    window_size_samples: int (default - 512 samples)
        !!! DEPRECATED, DOES NOTHING !!!

    Returns
    ----------
    speeches: list of dicts
        list containing ends and beginnings of speech chunks (samples or seconds based on return_seconds)
    """
    if not torch.is_tensor(audio):
        try:
            audio = torch.Tensor(audio)
        except:
            raise TypeError("Audio cannot be casted to tensor. Cast it manually")

    if len(audio.shape) > 1:
        for i in range(len(audio.shape)):  # trying to squeeze empty dimensions
            audio = audio.squeeze(0)
        if len(audio.shape) > 1:
            raise ValueError("More than one dimension in audio. Are you trying to process audio with 2 channels?")

    if sampling_rate > 16000 and (sampling_rate % 16000 == 0):
        step = sampling_rate // 16000
        sampling_rate = 16000
        audio = audio[::step]
        warnings.warn('Sampling rate is a multiply of 16000, casting to 16000 manually!')
    else:
        step = 1

    if sampling_rate not in [8000, 16000]:
        raise ValueError("Currently silero VAD models support 8000 and 16000 (or multiply of 16000) sample rates")

    window_size_samples = 512 if sampling_rate == 16000 else 256

    model.reset_states()
    min_speech_samples = sampling_rate * min_speech_duration_ms / 1000
    speech_pad_samples = sampling_rate * speech_pad_ms / 1000
    max_speech_samples = sampling_rate * max_speech_duration_s - window_size_samples - 2 * speech_pad_samples
    min_silence_samples = sampling_rate * min_silence_duration_ms / 1000
    min_silence_samples_at_max_speech = sampling_rate * min_silence_at_max_speech / 1000

    audio_length_samples = len(audio)

    speech_probs = []
    for current_start_sample in range(0, audio_length_samples, window_size_samples):
        chunk = audio[current_start_sample: current_start_sample + window_size_samples]
        if len(chunk) < window_size_samples:
            chunk = torch.nn.functional.pad(chunk, (0, int(window_size_samples - len(chunk))))
        speech_prob = model(chunk, sampling_rate).item()
        speech_probs.append(speech_prob)
        # calculate progress and send it to callback function
        progress = current_start_sample + window_size_samples
        if progress > audio_length_samples:
            progress = audio_length_samples
        progress_percent = (progress / audio_length_samples) * 100
        if progress_tracking_callback:
            progress_tracking_callback(progress_percent)

    triggered = False
    speeches = []
    current_speech = {}

    if neg_threshold is None:
        neg_threshold = max(threshold - 0.15, 0.01)
    temp_end = 0  # to save potential segment end (and tolerate some silence)
    prev_end = next_start = 0  # to save potential segment limits in case of maximum segment size reached
    possible_ends = []

    for i, speech_prob in enumerate(speech_probs):
        cur_sample = window_size_samples * i

        # If speech returns after a temp_end, record candidate silence if long enough and clear temp_end
        if (speech_prob >= threshold) and temp_end:
            sil_dur = cur_sample - temp_end
            if sil_dur > min_silence_samples_at_max_speech:
                possible_ends.append((temp_end, sil_dur))
            temp_end = 0
            if next_start < prev_end:
                next_start = cur_sample

        # Start of speech
        if (speech_prob >= threshold) and not triggered:
            triggered = True
            current_speech['start'] = cur_sample
            continue

        # Max speech length reached: decide where to cut
        if triggered and (cur_sample - current_speech['start'] > max_speech_samples):
            if use_max_poss_sil_at_max_speech and possible_ends:
                prev_end, dur = max(possible_ends, key=lambda x: x[1])  # use the longest possible silence segment in the current speech chunk
                current_speech['end'] = prev_end
                speeches.append(current_speech)
                current_speech = {}
                next_start = prev_end + dur

                if next_start < prev_end + cur_sample:  # previously reached silence (< neg_thres) and is still not speech (< thres)
                    current_speech['start'] = next_start
                else:
                    triggered = False
                prev_end = next_start = temp_end = 0
                possible_ends = []
            else:
                # Legacy max-speech cut (use_max_poss_sil_at_max_speech=False): prefer last valid silence (prev_end) if available
                if prev_end:
                    current_speech['end'] = prev_end
                    speeches.append(current_speech)
                    current_speech = {}
                    if next_start < prev_end:
                        triggered = False
                    else:
                        current_speech['start'] = next_start
                    prev_end = next_start = temp_end = 0
                    possible_ends = []
                else:
                    # No prev_end -> fallback to cutting at current sample
                    current_speech['end'] = cur_sample
                    speeches.append(current_speech)
                    current_speech = {}
                    prev_end = next_start = temp_end = 0
                    triggered = False
                    possible_ends = []
                    continue

        # Silence detection while in speech
        if (speech_prob < neg_threshold) and triggered:
            if not temp_end:
                temp_end = cur_sample
            sil_dur_now = cur_sample - temp_end

            if not use_max_poss_sil_at_max_speech and sil_dur_now > min_silence_samples_at_max_speech:  # condition to avoid cutting in very short silence
                prev_end = temp_end

            if sil_dur_now < min_silence_samples:
                continue
            else:
                current_speech['end'] = temp_end
                if (current_speech['end'] - current_speech['start']) > min_speech_samples:
                    speeches.append(current_speech)
                current_speech = {}
                prev_end = next_start = temp_end = 0
                triggered = False
                possible_ends = []
                continue

    if current_speech and (audio_length_samples - current_speech['start']) > min_speech_samples:
        current_speech['end'] = audio_length_samples
        speeches.append(current_speech)

    for i, speech in enumerate(speeches):
        if i == 0:
            speech['start'] = int(max(0, speech['start'] - speech_pad_samples))
        if i != len(speeches) - 1:
            silence_duration = speeches[i+1]['start'] - speech['end']
            if silence_duration < 2 * speech_pad_samples:
                speech['end'] += int(silence_duration // 2)
                speeches[i+1]['start'] = int(max(0, speeches[i+1]['start'] - silence_duration // 2))
            else:
                speech['end'] = int(min(audio_length_samples, speech['end'] + speech_pad_samples))
                speeches[i+1]['start'] = int(max(0, speeches[i+1]['start'] - speech_pad_samples))
        else:
            speech['end'] = int(min(audio_length_samples, speech['end'] + speech_pad_samples))

    if return_seconds:
        audio_length_seconds = audio_length_samples / sampling_rate
        for speech_dict in speeches:
            speech_dict['start'] = max(round(speech_dict['start'] / sampling_rate, time_resolution), 0)
            speech_dict['end'] = min(round(speech_dict['end'] / sampling_rate, time_resolution), audio_length_seconds)
    elif step > 1:
        for speech_dict in speeches:
            speech_dict['start'] *= step
            speech_dict['end'] *= step

    if visualize_probs:
        make_visualization(speech_probs, window_size_samples / sampling_rate)

    return speeches


class VADIterator:
    def __init__(self,
                 model,
                 threshold: float = 0.5,
                 sampling_rate: int = 16000,
                 min_silence_duration_ms: int = 100,
                 speech_pad_ms: int = 30
                 ):

        """
        Class for stream imitation

        Parameters
        ----------
        model: preloaded .jit/.onnx silero VAD model

        threshold: float (default - 0.5)
            Speech threshold. Silero VAD outputs speech probabilities for each audio chunk, probabilities ABOVE this value are considered as SPEECH.
            It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets.

        sampling_rate: int (default - 16000)
            Currently silero VAD models support 8000 and 16000 sample rates

        min_silence_duration_ms: int (default - 100 milliseconds)
            In the end of each speech chunk wait for min_silence_duration_ms before separating it

        speech_pad_ms: int (default - 30 milliseconds)
            Final speech chunks are padded by speech_pad_ms each side
        """

        self.model = model
        self.threshold = threshold
        self.sampling_rate = sampling_rate

        if sampling_rate not in [8000, 16000]:
            raise ValueError('VADIterator does not support sampling rates other than [8000, 16000]')

        self.min_silence_samples = sampling_rate * min_silence_duration_ms / 1000
        self.speech_pad_samples = sampling_rate * speech_pad_ms / 1000
        self.reset_states()

    def reset_states(self):

        self.model.reset_states()
        self.triggered = False
        self.temp_end = 0
        self.current_sample = 0

    @torch.no_grad()
    def __call__(self, x, return_seconds=False, time_resolution: int = 1):
        """
        x: torch.Tensor
            audio chunk (see examples in repo)

        return_seconds: bool (default - False)
            whether return timestamps in seconds (default - samples)

        time_resolution: int (default - 1)
            time resolution of speech coordinates when requested as seconds
        """

        if not torch.is_tensor(x):
            try:
                x = torch.Tensor(x)
            except:
                raise TypeError("Audio cannot be casted to tensor. Cast it manually")

        window_size_samples = len(x[0]) if x.dim() == 2 else len(x)
        self.current_sample += window_size_samples

        speech_prob = self.model(x, self.sampling_rate).item()

        if (speech_prob >= self.threshold) and self.temp_end:
            self.temp_end = 0

        if (speech_prob >= self.threshold) and not self.triggered:
            self.triggered = True
            speech_start = max(0, self.current_sample - self.speech_pad_samples - window_size_samples)
            return {'start': int(speech_start) if not return_seconds else round(speech_start / self.sampling_rate, time_resolution)}

        if (speech_prob < self.threshold - 0.15) and self.triggered:
            if not self.temp_end:
                self.temp_end = self.current_sample
            if self.current_sample - self.temp_end < self.min_silence_samples:
                return None
            else:
                speech_end = self.temp_end + self.speech_pad_samples - window_size_samples
                self.temp_end = 0
                self.triggered = False
                return {'end': int(speech_end) if not return_seconds else round(speech_end / self.sampling_rate, time_resolution)}

        return None


def collect_chunks(tss: List[dict],
                   wav: torch.Tensor,
                   seconds: bool = False,
                   sampling_rate: int = None) -> torch.Tensor:
    """Collect audio chunks from a longer audio clip

    This method extracts audio chunks from an audio clip, using a list of
    provided coordinates, and concatenates them together. Coordinates can be
    passed either as sample numbers or in seconds, in which case the audio
    sampling rate is also needed.

    Parameters
    ----------
    tss: List[dict]
        Coordinate list of the clips to collect from the audio.
    wav: torch.Tensor, one dimensional
        One dimensional float torch.Tensor, containing the audio to clip.
    seconds: bool (default - False)
        Whether input coordinates are passed as seconds or samples.
    sampling_rate: int (default - None)
        Input audio sampling rate. Required if seconds is True.

    Returns
    -------
    torch.Tensor, one dimensional
        One dimensional float torch.Tensor of the concatenated clipped audio
        chunks.

    Raises
    ------
    ValueError
        Raised if sampling_rate is not provided when seconds is True.

    """
    if seconds and not sampling_rate:
        raise ValueError('sampling_rate must be provided when seconds is True')

    chunks = list()
    _tss = _seconds_to_samples_tss(tss, sampling_rate) if seconds else tss

    for i in _tss:
        chunks.append(wav[i['start']:i['end']])

    return torch.cat(chunks)


def drop_chunks(tss: List[dict],
                wav: torch.Tensor,
                seconds: bool = False,
                sampling_rate: int = None) -> torch.Tensor:
    """Drop audio chunks from a longer audio clip

    This method extracts audio chunks from an audio clip, using a list of
    provided coordinates, and drops them. Coordinates can be passed either as
    sample numbers or in seconds, in which case the audio sampling rate is also
    needed.

    Parameters
    ----------
    tss: List[dict]
        Coordinate list of the clips to drop from from the audio.
    wav: torch.Tensor, one dimensional
        One dimensional float torch.Tensor, containing the audio to clip.
    seconds: bool (default - False)
        Whether input coordinates are passed as seconds or samples.
    sampling_rate: int (default - None)
        Input audio sampling rate. Required if seconds is True.

    Returns
    -------
    torch.Tensor, one dimensional
        One dimensional float torch.Tensor of the input audio minus the dropped
        chunks.

    Raises
    ------
    ValueError
        Raised if sampling_rate is not provided when seconds is True.

    """
    if seconds and not sampling_rate:
        raise ValueError('sampling_rate must be provided when seconds is True')

    chunks = list()
    cur_start = 0

    _tss = _seconds_to_samples_tss(tss, sampling_rate) if seconds else tss

    for i in _tss:
        chunks.append((wav[cur_start: i['start']]))
        cur_start = i['end']

    chunks.append(wav[cur_start:])

    return torch.cat(chunks)


def _seconds_to_samples_tss(tss: List[dict], sampling_rate: int) -> List[dict]:
    """Convert coordinates expressed in seconds to sample coordinates.
    """
    return [{
        'start': round(crd['start']) * sampling_rate,
        'end': round(crd['end']) * sampling_rate
    } for crd in tss]
