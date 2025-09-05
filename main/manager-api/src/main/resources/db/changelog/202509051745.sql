-- 添加 MinimaxHTTPStream 流式 TTS 供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_MinimaxStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_MinimaxStreamTTS', 'TTS', 'minimax_httpstream', 'Minimax流式语音合成', '[{"key":"group_id","label":"组ID","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice_id","label":"音色ID","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice_setting","label":"音色设置","type":"dict","dict_name":"voice_setting"},{"key":"pronunciation_dict","label":"发音字典","type":"dict","dict_name":"pronunciation_dict"},{"key":"audio_setting","label":"音频设置","type":"dict","dict_name":"audio_setting"},{"key":"timber_weights","label":"音色权重","type":"string"}]', 18, 1, NOW(), 1, NOW());

-- 添加Minimax流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_MinimaxStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_MinimaxStreamTTS', 'TTS', 'MinimaxStreamTTS', 'Minimax流式语音合成', 0, 1, '{"type": "minimax_httpstream", "group_id": "", "api_key": "", "model": "speech-01-turbo", "voice_id": "female-shaonv", "output_dir": "tmp/", "voice_setting": {"speed": 1, "vol": 1, "pitch": 0, "emotion": "happy"}, "pronunciation_dict": {"tone": ["处理/(chu3)(li3)", "危险/dangerous"]}, "audio_setting": {"sample_rate": 24000, "bitrate": 128000, "format": "pcm", "channel": 1}}', NULL, NULL, 21, NULL, NULL, NULL, NULL);

-- 更新Minimax流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.minimaxi.com/',
`remark` = 'Minimax流式TTS配置说明：
1. 需要先申请Minimax API Key
2. 需要填写Group ID
3. 支持多种音色设置和音频参数调整
4. 支持实时流式合成，具有较低的延迟
5. 支持自定义发音字典和音色权重
6. 隐藏参数配置：声音设定(voice_setting)、发音字典(pronunciation_dict)、音色权重(timber_weights)
   - 语速(speed): 范围[0.5,2]，默认1.0，取值越大语速越快
   - 音量(vol): 范围(0,10]，默认1.0，取值越大音量越高
   - 音调(pitch): 范围[-12,12]，默认0，取值需为整数
   - 情绪(emotion): 控制合成语音的情绪，支持7种值：["happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm"]，该参数仅对 speech-2.5-hd-preview、speech-2.5-turbo-preview、speech-02-hd、speech-02-turbo、speech-01-turbo、speech-01-hd 生效
   - timbre_weights与voice_id二选一必填
   - voice_id(请求的音色id，须和weight参数同步填写)
   - weight(权重，最多支持4种音色混合。范围[1,100])
' WHERE `id` = 'TTS_MinimaxStreamTTS';

-- 添加Minimax流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_MinimaxStreamTTS';

-- 默认音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0001', 'TTS_MinimaxStreamTTS', '少女音', 'female-shaonv', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0002', 'TTS_MinimaxStreamTTS', '成熟女声', 'female-chengshu', '中文', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0003', 'TTS_MinimaxStreamTTS', '霸道少爷', 'badao_shaoye', '中文', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0004', 'TTS_MinimaxStreamTTS', '病娇弟弟', 'bingjiao_didi', '中文', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0005', 'TTS_MinimaxStreamTTS', '纯真学弟', 'chunzhen_xuedi', '中文', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0006', 'TTS_MinimaxStreamTTS', '冷淡学长', 'lengdan_xiongzhang', '中文', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0007', 'TTS_MinimaxStreamTTS', '甜美小玲', 'tianxin_xiaoling', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0008', 'TTS_MinimaxStreamTTS', '俏皮萌妹', 'qiaopi_mengmei', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0009', 'TTS_MinimaxStreamTTS', '妩媚御姐', 'wumei_yujie', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0010', 'TTS_MinimaxStreamTTS', '嗲嗲学妹', 'diadia_xuemei', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0011', 'TTS_MinimaxStreamTTS', '淡雅学姐', 'danya_xuejie', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0012', 'TTS_MinimaxStreamTTS', 'Santa Claus', 'Santa_Claus', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0013', 'TTS_MinimaxStreamTTS', 'Grinch', 'Grinch', '中文', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
