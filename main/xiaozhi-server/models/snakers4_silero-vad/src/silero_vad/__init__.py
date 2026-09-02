from importlib.metadata import version
try:
    __version__ = version(__name__)
except:
    pass

from silero_vad.model import load_silero_vad
from silero_vad.utils_vad import (get_speech_timestamps,
                                  save_audio,
                                  read_audio,
                                  VADIterator,
                                  collect_chunks,
                                  drop_chunks)
