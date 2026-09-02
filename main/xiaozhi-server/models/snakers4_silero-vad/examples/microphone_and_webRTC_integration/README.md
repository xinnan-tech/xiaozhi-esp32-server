
In this example, an integration with the microphone and the webRTC VAD has been done.  I used [this](https://github.com/mozilla/DeepSpeech-examples/tree/r0.8/mic_vad_streaming) as a draft.
Here a short video to present the results:

https://user-images.githubusercontent.com/28188499/116685087-182ff100-a9b2-11eb-927d-ed9f621226ee.mp4

# Requirements:
The libraries used for the following example are:
```
Python == 3.6.9
webrtcvad >= 2.0.10
torchaudio >= 0.8.1
torch >= 1.8.1
halo >= 0.0.31
Soundfile >= 0.13.3
```
Using pip3:
```
pip3 install webrtcvad
pip3 install torchaudio
pip3 install torch
pip3 install halo
pip3 install soundfile
```
Moreover, to make the code easier, the default sample_rate is 16KHz without resampling.

This example has been tested on ``` ubuntu 18.04.3 LTS```

