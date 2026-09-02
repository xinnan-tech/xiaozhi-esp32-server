import collections, queue
import numpy as np
import pyaudio
import webrtcvad
from halo import Halo
import torch
import torchaudio

class Audio(object):
    """Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from."""

    FORMAT = pyaudio.paInt16
    # Network/VAD rate-space
    RATE_PROCESS = 16000
    CHANNELS = 1
    BLOCKS_PER_SECOND = 50

    def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS):
        def proxy_callback(in_data, frame_count, time_info, status):
            #pylint: disable=unused-argument
            callback(in_data)
            return (None, pyaudio.paContinue)
        if callback is None: callback = lambda in_data: self.buffer_queue.put(in_data)
        self.buffer_queue = queue.Queue()
        self.device = device
        self.input_rate = input_rate
        self.sample_rate = self.RATE_PROCESS
        self.block_size = int(self.RATE_PROCESS / float(self.BLOCKS_PER_SECOND))
        self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECOND))
        self.pa = pyaudio.PyAudio()

        kwargs = {
            'format': self.FORMAT,
            'channels': self.CHANNELS,
            'rate': self.input_rate,
            'input': True,
            'frames_per_buffer': self.block_size_input,
            'stream_callback': proxy_callback,
        }

        self.chunk = None
        # if not default device
        if self.device:
            kwargs['input_device_index'] = self.device

        self.stream = self.pa.open(**kwargs)
        self.stream.start_stream()

    def read(self):
        """Return a block of audio data, blocking if necessary."""
        return self.buffer_queue.get()

    def destroy(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    frame_duration_ms = property(lambda self: 1000 * self.block_size // self.sample_rate)


class VADAudio(Audio):
    """Filter & segment audio with voice activity detection."""

    def __init__(self, aggressiveness=3, device=None, input_rate=None):
        super().__init__(device=device, input_rate=input_rate)
        self.vad = webrtcvad.Vad(aggressiveness)

    def frame_generator(self):
        """Generator that yields all audio frames from microphone."""
        if self.input_rate == self.RATE_PROCESS:
            while True:
                yield self.read()
        else:
            raise Exception("Resampling required")

    def vad_collector(self, padding_ms=300, ratio=0.75, frames=None):
        """Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
            Determines voice activity by ratio of frames in padding_ms. Uses a buffer to include padding_ms prior to being triggered.
            Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
                      |---utterence---|        |---utterence---|
        """
        if frames is None: frames = self.frame_generator()
        num_padding_frames = padding_ms // self.frame_duration_ms
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False

        for frame in frames:
            if len(frame) < 640:
                return

            is_speech = self.vad.is_speech(frame, self.sample_rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > ratio * ring_buffer.maxlen:
                    triggered = True
                    for f, s in ring_buffer:
                        yield f
                    ring_buffer.clear()

            else:
                yield frame
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > ratio * ring_buffer.maxlen:
                    triggered = False
                    yield None
                    ring_buffer.clear()

def main(ARGS):
    # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=ARGS.webRTC_aggressiveness,
                         device=ARGS.device,
                         input_rate=ARGS.rate)

    print("Listening (ctrl-C to exit)...")
    frames = vad_audio.vad_collector()

    # load silero VAD
    torchaudio.set_audio_backend("soundfile")
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                    model=ARGS.silaro_model_name,
                                    force_reload= ARGS.reload)
    (get_speech_ts,_,_, _,_, _, _) = utils


    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    wav_data = bytearray()
    for frame in frames:
        if frame is not None:
            if spinner: spinner.start()

            wav_data.extend(frame)
        else:
            if spinner: spinner.stop()
            print("webRTC has detected a possible speech")

            newsound= np.frombuffer(wav_data,np.int16)
            audio_float32=Int2Float(newsound)
            time_stamps =get_speech_ts(audio_float32, model,num_steps=ARGS.num_steps,trig_sum=ARGS.trig_sum,neg_trig_sum=ARGS.neg_trig_sum,
                                    num_samples_per_window=ARGS.num_samples_per_window,min_speech_samples=ARGS.min_speech_samples,
                                    min_silence_samples=ARGS.min_silence_samples)

            if(len(time_stamps)>0):
                print("silero VAD has detected a possible speech")
            else:
                print("silero VAD has detected a noise")
            print()
            wav_data = bytearray()


def Int2Float(sound):
    _sound = np.copy(sound)  #
    abs_max = np.abs(_sound).max()
    _sound = _sound.astype('float32')
    if abs_max > 0:
        _sound *= 1/abs_max
    audio_float32 = torch.from_numpy(_sound.squeeze())
    return audio_float32

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    import argparse
    parser = argparse.ArgumentParser(description="Stream from microphone to webRTC and silero VAD")

    parser.add_argument('-v', '--webRTC_aggressiveness', type=int, default=3,
                        help="Set aggressiveness of webRTC: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
    parser.add_argument('--nospinner', action='store_true',
                        help="Disable spinner")
    parser.add_argument('-d', '--device', type=int, default=None,
                        help="Device input index (Int) as listed by pyaudio.PyAudio.get_device_info_by_index(). If not provided, falls back to PyAudio.get_default_device().")

    parser.add_argument('-name', '--silaro_model_name', type=str, default="silero_vad",
                        help="select the name of the model. You can select between 'silero_vad',''silero_vad_micro','silero_vad_micro_8k','silero_vad_mini','silero_vad_mini_8k'")
    parser.add_argument('--reload', action='store_true',help="download the last version of the silero vad")

    parser.add_argument('-ts', '--trig_sum', type=float, default=0.25,
                        help="overlapping windows are used for each audio chunk, trig sum defines average probability among those windows for switching into triggered state (speech state)")

    parser.add_argument('-nts', '--neg_trig_sum', type=float, default=0.07,
                        help="same as trig_sum, but for switching from triggered to non-triggered state (non-speech)")

    parser.add_argument('-N', '--num_steps', type=int, default=8,
                        help="number of overlapping windows to split audio chunk into (we recommend 4 or 8)")

    parser.add_argument('-nspw', '--num_samples_per_window', type=int, default=4000,
                        help="number of samples in each window, our models were trained using 4000 samples (250 ms) per window, so this is preferable value (lesser values reduce quality)")

    parser.add_argument('-msps', '--min_speech_samples', type=int, default=10000,
                        help="minimum speech chunk duration in samples")

    parser.add_argument('-msis', '--min_silence_samples', type=int, default=500,
                        help=" minimum silence duration in samples between to separate speech chunks")
    ARGS = parser.parse_args()
    ARGS.rate=DEFAULT_SAMPLE_RATE
    main(ARGS)
