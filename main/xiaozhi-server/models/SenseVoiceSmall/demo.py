# 导入AutoModel类和rich_transcription_postprocess函数
# AutoModel是FunASR库中的一个类，用于加载和运行语音识别模型
# rich_transcription_postprocess用于对识别结果进行后处理，使其更加丰富和易读
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 定义模型目录路径，这里假设模型文件存储在当前目录下
model_dir = "./"

# 使用AutoModel加载模型
# model_dir: 模型文件所在的目录路径
# vad_model: 指定使用的语音活动检测(VAD)模型，这里使用的是"fsmn-vad"
# vad_kwargs: VAD模型的参数配置，这里设置最大单段语音时长为30000毫秒（即30秒）
# device: 指定运行模型的设备，例如"cuda:0"表示使用GPU，这里被注释掉了，默认使用CPU
# hub: 指定模型来源，这里使用"hf"表示从Hugging Face Hub加载模型
model = AutoModel(
    model=model_dir,
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    # device="cuda:0",
    hub="hf",
)

# 使用模型进行语音识别
# input: 指定输入的音频文件路径，这里使用的是模型目录下的example/en.mp3文件
# cache: 用于缓存中间结果，这里初始化为空字典
# language: 指定语音识别的语言，这里设置为"auto"表示自动检测语言
# use_itn: 是否使用逆文本归一化（Inverse Text Normalization），这里设置为True
# batch_size_s: 指定批处理的大小，单位为秒，这里设置为60秒
# merge_vad: 是否合并VAD检测到的语音段，这里设置为True
# merge_length_s: 合并语音段的最大长度，单位为秒，这里设置为15秒
res = model.generate(
    input=f"{model.model_path}/example/en.mp3",
    cache={},
    language="auto",  # 可选值："zn"（中文），"en"（英文），"yue"（粤语），"ja"（日语），"ko"（韩语），"nospeech"（无语音）
    use_itn=True,
    batch_size_s=60,
    merge_vad=True,  #
    merge_length_s=15,
)

# 对识别结果进行后处理
# res[0]["text"]: 获取识别结果中的文本部分
# rich_transcription_postprocess: 对文本进行后处理，使其更加丰富和易读
text = rich_transcription_postprocess(res[0]["text"])

# 打印处理后的文本
print(text)