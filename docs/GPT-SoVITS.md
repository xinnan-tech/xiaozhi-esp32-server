# GPT-SoVIST智控台語音管理設定

## 第一步 複製設定檔
用浏览器打开[这个链接](../main/xiaozhi-server/gpt_sovits.yaml)。

在页面的右侧找到名称为`RAW`按钮，在`RAW`按钮的旁边，找到下载的图标，点击下载按钮，下载`gpt_sovits.yaml`文件。 把文件下载到你的
`xiaozhi-server`下面的`data`文件夹中，然后把`gpt_sovits.yaml`文件重命名为`.voice.yaml`。

或者直接执行 `wget https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/gpt_sovits.yaml -O .voice.yaml` 下载保存。

## 第二步 配置.voice.yaml

使用v2就在v2底下添加新的人物音效，使用v3則在v3底下添加。
以下為v2範例
```yaml
v2:
  音色1:
    text_lang: 文本语言
    ref_audio_path: 参考音频路径(必填)
    prompt_text: 提示文本(必填)
    prompt_lang: 提示语言
  音色2:
    ref_audio_path: 参考音频路径(必填)
    prompt_text: 提示文本(必填)
```
以下為v3範例
```yaml
v3:
  音色1:
    text_language: 文本语言
    refer_wav_path: 参考音频路径(必填)
    prompt_text: 提示文本(必填)
    prompt_language: 提示语言
  音色2:
    refer_wav_path: 参考音频路径(必填)
    prompt_text: 提示文本(必填)
```
音色名稱可以自訂

## 第三步 設定音色管理

使用管理員帳號登入 智控台 -> 模型配置 -> 到GPT-SoVITS的音色管理 -> 點擊新增 應該會看到以下畫面。
![img.png](./images/img-GPT_SoVITS.png)
音色編碼對應到的是設定檔中的音色1或自訂的音色名稱，音色名稱則是在角色音色中顯示的名稱。

## 其他可用選項
### v2:
```yaml
音色編碼:
  text_lang: 文本语言
  ref_audio_path: 参考音频路径(必填)
  aux_ref_audio_paths: 辅助参考音频路径
  prompt_text: 提示文本(必填)
  prompt_lang: 提示语言
  top_k: top_k值
  top_p: top_p值
  temperature: 温度
  batch_threshold: 批处理阈值
  batch_size: 批处理大小
  speed_factor: 速度因子
  seed: 种子
  repetition_penalty: 重复惩罚
```
### v3: 
```yaml
音色編碼:
  text_language: 文本语言
  refer_wav_path: 参考音频路径(必填)
  inp_refs: 输入参考
  prompt_text: 提示文本(必填)
  prompt_language: 提示语言
  top_k: top_k值
  top_p: top_p值
  temperature: 温度
  sample_steps: 采样步数
  speed: 速度
  cut_punc: 切分标点
```
