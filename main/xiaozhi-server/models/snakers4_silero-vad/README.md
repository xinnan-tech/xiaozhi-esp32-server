[![Mailing list : test](http://img.shields.io/badge/Email-gray.svg?style=for-the-badge&logo=gmail)](mailto:hello@silero.ai) [![Mailing list : test](http://img.shields.io/badge/Telegram-blue.svg?style=for-the-badge&logo=telegram)](https://t.me/silero_speech) [![License: CC BY-NC 4.0](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=for-the-badge)](https://github.com/snakers4/silero-vad/blob/master/LICENSE) [![downloads](https://img.shields.io/pypi/dm/silero-vad?style=for-the-badge)](https://pypi.org/project/silero-vad/) 

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/snakers4/silero-vad/blob/master/silero-vad.ipynb) [![Test Package](https://github.com/snakers4/silero-vad/actions/workflows/test.yml/badge.svg)](https://github.com/snakers4/silero-vad/actions/workflows/test.yml) [![Pypi version](https://img.shields.io/pypi/v/silero-vad)](https://pypi.org/project/silero-vad/) [![Python version](https://img.shields.io/pypi/pyversions/silero-vad)](https://pypi.org/project/silero-vad)

![header](https://user-images.githubusercontent.com/12515440/89997349-b3523080-dc94-11ea-9906-ca2e8bc50535.png)

<br/>
<h1 align="center">Silero VAD</h1>
<br/>

**Silero VAD** - pre-trained enterprise-grade [Voice Activity Detector](https://en.wikipedia.org/wiki/Voice_activity_detection) (also see our [STT models](https://github.com/snakers4/silero-models)).

<br/>

<p align="center">
  <img src="https://github.com/user-attachments/assets/f2940867-0a51-4bdb-8c14-1129d3c44e64" />
</p>


<details>
<summary>Real Time Example</summary>

https://user-images.githubusercontent.com/36505480/144874384-95f80f6d-a4f1-42cc-9be7-004c891dd481.mp4

Please note, that video loads only if you are logged in your GitHub account. 

</details>

<br/>

<h2 align="center">Fast start</h2>
<br/>

<details>
<summary>Dependencies</summary>

  System requirements to run python examples on `x86-64` systems:
  
  - `python 3.8+`;
  - 1G+ RAM;
  - A modern CPU with AVX, AVX2, AVX-512 or AMX instruction sets.

  Dependencies:
  
  - `torch>=1.12.0`;
  - `torchaudio>=0.12.0` (for I/O only);
  - `onnxruntime>=1.16.1` (for ONNX model usage).
  
  Silero VAD uses torchaudio library for audio I/O (`torchaudio.info`, `torchaudio.load`, and `torchaudio.save`), so a proper audio backend is required:
  
  - Option №1 - [**FFmpeg**](https://www.ffmpeg.org/) backend. `conda install -c conda-forge 'ffmpeg<7'`;
  - Option №2 - [**sox_io**](https://pypi.org/project/sox/) backend. `apt-get install sox`, TorchAudio is tested on libsox 14.4.2;
  - Option №3 - [**soundfile**](https://pypi.org/project/soundfile/) backend. `pip install soundfile`.

If you are planning to run the VAD using solely the `onnx-runtime`, it will run on any other system architectures where onnx-runtume is [supported](https://onnxruntime.ai/getting-started). In this case please note that:

- You will have to implement the I/O;
- You will have to adapt the existing wrappers / examples / post-processing for your use-case.

</details>

**Using pip**:
`pip install silero-vad`

```python3
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
model = load_silero_vad()
wav = read_audio('path_to_audio_file')
speech_timestamps = get_speech_timestamps(
  wav,
  model,
  return_seconds=True,  # Return speech timestamps in seconds (default is samples)
)
```

**Using torch.hub**:
```python3
import torch
torch.set_num_threads(1)

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
(get_speech_timestamps, _, read_audio, _, _) = utils

wav = read_audio('path_to_audio_file')
speech_timestamps = get_speech_timestamps(
  wav,
  model,
  return_seconds=True,  # Return speech timestamps in seconds (default is samples)
)
```

<br/>

<h2 align="center">Key Features</h2>
<br/>

- **Stellar accuracy**

  Silero VAD has [excellent results](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics#vs-other-available-solutions) on speech detection tasks.
  
- **Fast**

  One audio chunk (30+ ms) [takes](https://github.com/snakers4/silero-vad/wiki/Performance-Metrics#silero-vad-performance-metrics) less than **1ms** to be processed on a single CPU thread. Using batching or GPU can also improve performance considerably. Under certain conditions ONNX may even run up to 4-5x faster. 

- **Lightweight**

  JIT model is around two megabytes in size.

- **General**

  Silero VAD was trained on huge corpora that include over **6000** languages and it performs well on audios from different domains with various background noise and quality levels.

- **Flexible sampling rate**

  Silero VAD [supports](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics#sample-rate-comparison)  **8000 Hz** and **16000 Hz** [sampling rates](https://en.wikipedia.org/wiki/Sampling_(signal_processing)#Sampling_rate).

- **Highly Portable**

  Silero VAD reaps benefits from the rich ecosystems built around **PyTorch** and **ONNX** running everywhere where these runtimes are available.

- **No Strings Attached**

   Published under permissive license (MIT) Silero VAD has zero strings attached - no telemetry, no keys, no registration, no built-in expiration, no keys or vendor lock.

<br/>

<h2 align="center">Typical Use Cases</h2>
<br/>

- Voice activity detection for IOT / edge / mobile use cases
- Data cleaning and preparation, voice detection in general
- Telephony and call-center automation, voice bots
- Voice interfaces

<br/>
<h2 align="center">Links</h2>
<br/>


- [Examples and Dependencies](https://github.com/snakers4/silero-vad/wiki/Examples-and-Dependencies#dependencies)
- [Quality Metrics](https://github.com/snakers4/silero-vad/wiki/Quality-Metrics)
- [Performance Metrics](https://github.com/snakers4/silero-vad/wiki/Performance-Metrics)
- [Versions and Available Models](https://github.com/snakers4/silero-vad/wiki/Version-history-and-Available-Models)
- [Further reading](https://github.com/snakers4/silero-models#further-reading)
- [FAQ](https://github.com/snakers4/silero-vad/wiki/FAQ)

<br/>
<h2 align="center">Get In Touch</h2>
<br/>

Try our models, create an [issue](https://github.com/snakers4/silero-vad/issues/new), start a [discussion](https://github.com/snakers4/silero-vad/discussions/new), join our telegram [chat](https://t.me/silero_speech), [email](mailto:hello@silero.ai) us, read our [news](https://t.me/silero_news).

Please see our [wiki](https://github.com/snakers4/silero-models/wiki) for relevant information and [email](mailto:hello@silero.ai) us directly.

**Citations**

```
@misc{Silero VAD,
  author = {Silero Team},
  title = {Silero VAD: pre-trained enterprise-grade Voice Activity Detector (VAD), Number Detector and Language Classifier},
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/snakers4/silero-vad}},
  commit = {insert_some_commit_here},
  email = {hello@silero.ai}
}
```

<br/>
<h2 align="center">Examples and VAD-based Community Apps</h2>
<br/>

- Example of VAD ONNX Runtime model usage in [C++](https://github.com/snakers4/silero-vad/tree/master/examples/cpp) 

- Voice activity detection for the [browser](https://github.com/ricky0123/vad) using ONNX Runtime Web

- [Rust](https://github.com/snakers4/silero-vad/tree/master/examples/rust-example), [Go](https://github.com/snakers4/silero-vad/tree/master/examples/go), [Java](https://github.com/snakers4/silero-vad/tree/master/examples/java-example), [C++](https://github.com/snakers4/silero-vad/tree/master/examples/cpp), [C#](https://github.com/snakers4/silero-vad/tree/master/examples/csharp) and [other](https://github.com/snakers4/silero-vad/tree/master/examples) community examples
