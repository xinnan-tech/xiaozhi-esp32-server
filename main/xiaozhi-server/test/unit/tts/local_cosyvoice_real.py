import os
import unittest
import time
from datetime import datetime
import uuid
import wave
import torchaudio
from core.providers.tts.local_cosyvoice import TTSProvider


class TestRealTTSGeneration(unittest.TestCase):
    """真实语音生成集成测试，需要实际的 CosyVoice 环境"""

    def setUp(self):
        # 使用真实配置 - 请确保这些路径在您的环境中有效
        self.config = {
            "output_dir": "/tmp",
            "cosyvoice_path": "/home/shangjun/xt_workspace/python_workspace/CosyVoice",
            "cosyvoice_model_dir": "/home/shangjun/xt_workspace/python_workspace/CosyVoice/pretrained_models/CosyVoice2-0.5B",
            "prompt_speech_16k": "/home/shangjun/xt_workspace/python_workspace/CosyVoice/asset/zero_shot_prompt.wav",
            "prompt_speech_16k_text": "希望你以后能够做的比我还好呦。"
        }
        # 创建输出目录
        os.makedirs(self.config["output_dir"], exist_ok=True)

    def test_real_tts_generation(self):
        """使用真实模型生成语音文件"""
        # 初始化提供者，不删除生成的文件
        provider = TTSProvider(self.config, False)
        provider.format = "wav"

        # 生成测试文本
        test_text = "王骀受了刖刑，被砍去了一只脚。孔子有个弟子叫常季，他见老师时提出了自己的疑问。他说：老师你看，王骀被砍去了一只脚，可是他的学识和品行好像都超过了先生您，至于跟平常人相比，好像水平就更高了。像他这样的人，运用心智是怎样的与众不同呢？孔子的学生觉得很是奇怪，这个人一只脚被砍掉了，但是他的名声却很大，很多人都喜欢跟他学习，这个学生感到很不理解，一见到老师就向老师提出自己心中的疑问。文中庄子又是借孔子之口，表达了自己这样的观点：说死和生都是人生中的大事，可是死和生都不能使王骀这样的人随之变化，你说王骀是个什么样的人呢？即使天翻过来地坠下去，他也不会因此而被毁灭，他通晓无所依凭的道理，当然也就不随物变迁，而是听任事物的变化而信守自己的宗本。孔子的这段话把常季给说晕了，他忍不住再问：老师您这些话是什么意思啊？孔子怎么回答的呢？这段话很重要，来看一下完整的译文：孔子说：“从事物千差万别的一面去看，邻近的肝胆虽处于一体之中，也像是楚国和越国那样相距甚远；如果从事物相同的一面来看，万事万物又都是同一的，没有差别的。像王骀这样的人，耳朵和眼睛最适宜何种声音和色彩这样的事，已经不在他考虑范围之内了。他让自己的心思自由自在地遨游在忘形、忘情的浑同境域之中，就把这些东西的差别都忘掉了。所以他看待自己丧失了一只脚这件事，就像是看待失落的土块一样。”学了前面《庄子》的几篇文章，这段话的观点我们已不陌生。另外，有没有觉得这段话的句式很熟悉？中学时我们就学过苏东坡的《前赤壁赋》，其中就有这样的句式：“自其变者而观之，则天地曾不能以一瞬；自其不变者而观之，则物与我皆无尽也。”可以说，东坡不仅化用了庄子的句式，而且思想也和庄子是一样的。"

        # 执行文本到语音转换
        start_time = time.time()
        result_file = provider.to_tts(test_text)
        end_time = time.time()

        # 输出生成信息
        print(f"语音生成耗时: {end_time - start_time:.2f}秒")
        print(f"生成的文件路径: {result_file}")

        # 验证文件是否存在
        self.assertTrue(os.path.exists(result_file), "语音文件未成功生成")

        # 验证文件格式
        self.assertTrue(result_file.endswith(".wav"), "生成的不是WAV文件")

        # 验证文件内容
        try:
            # 检查音频文件属性
            audio_info = torchaudio.info(result_file)
            print(f"采样率: {audio_info.sample_rate}Hz")
            print(f"声道数: {audio_info.num_channels}")
            print(f"音频长度: {audio_info.num_frames / audio_info.sample_rate:.2f}秒")

            # 加载音频文件
            waveform, sample_rate = torchaudio.load(result_file)

            # 验证音频基本特性
            self.assertEqual(sample_rate, 24000, "采样率应为24kHz")
            self.assertTrue(waveform.size(0) > 0, "音频数据不应为空")
            self.assertTrue(waveform.size(1) > 0, "音频长度不应为0")

            print(f"音频形状: {waveform.shape}")
            print(f"最大值: {waveform.max().item():.4f}, 最小值: {waveform.min().item():.4f}")

        except Exception as e:
            self.fail(f"验证音频文件失败: {e}")

        # 如果需要，可以在这里播放音频进行人工验证
        # import IPython.display as ipd
        # ipd.Audio(result_file)

    def tearDown(self):
        # 清理临时文件(可选)
        # 注意：如果想保留文件以便检查，可以注释掉下面的代码
        # import shutil
        # shutil.rmtree(self.config["output_dir"])
        pass