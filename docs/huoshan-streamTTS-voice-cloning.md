# 火山双向流式TTS+声音克隆配置教程
单模块部署下，使用火山引擎双向流式语音合成服务的同时进行声音克隆，支持WebSocket协议流式调用。
### 1.开通火山引擎服务
访问 https://console.volcengine.com/speech/app  在应用管理创建应用，勾选语音合成大模型和声音复刻大模型，左边列表点击声音复刻大模型后下滑获得App Id，Access Token，Cluster ID以及声音ID(S_xxxxx)
### 2.克隆音色
克隆音色请参照教程 https://github.com/104gogo/huoshan-voice-copy 

准备一段 10-30 秒的音频文件（.wav格式）添加到克隆的项目中，将平台获得的密钥填入```uploadAndStatus.py```和```tts_http_demo.py```

在uploadAndStatus.py中，将 audio_path=修改成自己的.wav文件名称
```python
train(appid=appid, token=token, audio_path=r".\audios\xiaohe.wav", spk_id=spk_id)
```

运行以下命令生成test_submit.mp3，点击播放试听克隆效果

```python
python uploadAndStatus.py
python tts_http_demo.py
```
回到火山引擎控制台页面，刷新可以看到声音复刻详情的状态是复刻成功。
### 3.填写配置文件
将火山引擎服务申请到的密钥填入.config.yaml的HuoshanDoubleStreamTTS配置文件中

修改 resource_id的参数为``` volc.megatts.default``` 
（参考官方文档 https://www.volcengine.com/docs/6561/1329505）
speaker的参数填入声音ID(S_xxxxx)

启动服务，唤醒小智发出的声音是克隆的音色即成功。
