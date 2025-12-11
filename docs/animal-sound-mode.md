# 动物互动音频模式

让大语言模型给出情绪标签（如“开心”“悲伤”“生气”“害怕”“无奈”“撒娇”），服务器根据情绪播放对应动物叫声，将结果推送给小智客户端。

## 启用步骤
1. 准备音频文件（建议 16k/mono 的 wav 或 mp3），放到 `config/assets/animal_sounds/`，文件名与情绪映射参考下方配置。
2. 在 `data/.config.yaml`（或智控台 TTS 配置）里选择新的 TTS 模块 `AnimalSound`，并配置情绪到音频文件的映射：
   ```yaml
   selected_module:
     TTS: AnimalSound

   TTS:
     AnimalSound:
       type: animal_sound
       base_path: config/assets/animal_sounds
       emotion_files:
         happy: cat_happy.wav
         sad: cat_sad.wav
         angry: cat_angry.wav
         afraid: cat_afraid.wav
         helpless: cat_helpless.wav
         coquetry: cat_coquetry.wav
         default: cat_neutral.wav
       # 如果没有 default，可用绝对路径兜底
       # default_file: /abs/path/to/animal_default.wav
   ```
3. 确保对话输出包含情绪关键词，上述关键词会被自动匹配（可通过 `emotion_keywords` 自定义）。
4. 重启服务后生效。

## 行为说明
- 不会做文本合成，直接播放对应音频；找不到音频时仅记录警告。
- 关键词默认映射（可通过配置覆盖）：
  - happy: 开心/高兴/快乐/喜悦
  - sad: 悲伤/难过/伤心/沮丧
  - angry: 生气/愤怒/气愤
  - afraid: 害怕/恐惧/紧张
  - helpless: 无奈/唉/叹气
  - coquetry: 撒娇/卖萌/黏人

