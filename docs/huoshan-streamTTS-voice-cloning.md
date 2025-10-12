# Volcano Bidirectional Streaming TTS + Voice Cloning Configuration Tutorial
In a single-module deployment, voice cloning is performed while using the Volcano Engine bidirectional streaming speech synthesis service, supporting WebSocket protocol streaming calls.
### 1. Open the Volcano Engine service
Visit https://console.volcengine.com/speech/app and create an app in the App Manager. Select the speech synthesis model and the sound replication model. Click the sound replication model in the list on the left and scroll down to obtain the App ID, Access Token, Cluster ID, and Sound ID (S_xxxxx).
### 2. Clone the sound
To clone the voice, please refer to the tutorial https://github.com/104gogo/huoshan-voice-copy

Prepare a 10-30 second audio file (.wav format) and add it to the cloned project. Fill the key obtained from the platform into ```uploadAndStatus.py``` and ```tts_http_demo.py```

In uploadAndStatus.py, change audio_path= to your own .wav file name
```Python
train(appid=appid, token=token, audio_path=r".\audios\xiaohe.wav", spk_id=spk_id)
```

Run the following command to generate test_submit.mp3 and click Play to listen to the cloned effect.

```Python
python uploadAndStatus.py
python tts_http_demo.py
```
Go back to the Volcano Engine console page and refresh it to see that the status of the sound replication details is successful.
### 3. Fill in the configuration file
Fill in the key applied for by the Volcano Engine service into the HuoshanDoubleStreamTTS configuration file in .config.yaml

Modify the resource_id parameter to ``` volc.megatts.default```
(See the official documentation at https://www.volcengine.com/docs/6561/1329505)
Fill in the sound ID (S_xxxxx) of the speaker parameter

Start the service. If the sound produced by Xiaozhi when waking him up is the cloned one, it means success.
