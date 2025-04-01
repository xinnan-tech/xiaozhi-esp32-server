-- 本文件用于初始化音色数据，无需手动执行，在项目启动时会自动执行
-- ----------------------------------------------------

-- 初始化音色数据
DELETE FROM `ai_tts_voice`;

-- EdgeTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_EdgeTTS0001', 'TTS_EdgeTTS', 'EdgeTTS女声', 'zh-CN-XiaoxiaoNeural', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/EdgeTTS.mp3', NULL, 1, NULL, NULL, NULL, NULL);

-- DoubaoTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0001', 'TTS_DoubaoTTS', '通用女声', 'BV001_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV001.mp3', NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0002', 'TTS_DoubaoTTS', '通用男声', 'BV002_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV002.mp3', NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0003', 'TTS_DoubaoTTS', '阳光男生', 'BV056_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV056.mp3', NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0004', 'TTS_DoubaoTTS', '奶气萌娃', 'BV051_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV051.mp3', NULL, 5, NULL, NULL, NULL, NULL);

-- CosyVoiceSiliconflow音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0001', 'TTS_CosyVoiceSiliconflow', 'CosyVoice男声', 'alex', '中文', 'https://example.com/cosyvoice/alex.mp3', NULL, 6, NULL, NULL, NULL, NULL);

-- CozeCnTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_CozeCnTTS0001', 'TTS_CozeCnTTS', 'CozeCn音色', '7426720361733046281', '中文', 'https://example.com/cozecn/voice.mp3', NULL, 7, NULL, NULL, NULL, NULL);

-- MinimaxTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxTTS0001', 'TTS_MinimaxTTS', 'Minimax少女音', 'female-shaonv', '中文', 'https://example.com/minimax/female-shaonv.mp3', NULL, 8, NULL, NULL, NULL, NULL);

-- AliyunTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunTTS0001', 'TTS_AliyunTTS', '阿里云小云', 'xiaoyun', '中文', 'https://example.com/aliyun/xiaoyun.mp3', NULL, 9, NULL, NULL, NULL, NULL);

-- TTS302AI音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_TTS302AI0001', 'TTS_TTS302AI', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://example.com/302ai/wanwanxiaohe.mp3', NULL, 10, NULL, NULL, NULL, NULL);

-- GizwitsTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_GizwitsTTS0001', 'TTS_GizwitsTTS', '机智云湾湾', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://example.com/gizwits/wanwanxiaohe.mp3', NULL, 11, NULL, NULL, NULL, NULL);

-- ACGNTTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_ACGNTTS0001', 'TTS_ACGNTTS', 'ACG音色', '1695', '中文', 'https://example.com/acgn/voice.mp3', NULL, 12, NULL, NULL, NULL, NULL);

-- OpenAITTS音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_OpenAITTS0001', 'TTS_OpenAITTS', 'OpenAI男声', 'onyx', '中文', 'https://example.com/openai/onyx.mp3', NULL, 13, NULL, NULL, NULL, NULL);

-- 其他音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_FishSpeech0000', 'TTS_FishSpeech', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_GPT_SOVITS_V20000', 'TTS_GPT_SOVITS_V2', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_GPT_SOVITS_V30000', 'TTS_GPT_SOVITS_V3', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_CustomTTS0000', 'TTS_CustomTTS', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);