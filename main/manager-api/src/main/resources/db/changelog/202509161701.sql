-- 添加阿里百炼流式TTS 供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_AliBLStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_AliBLStreamTTS', 'TTS', 'alibl_stream', '阿里百炼流式语音合成', '[{"key":"api_key","label":"API密钥","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key": "volume", "type": "number", "label": "音量"},{"key": "rate", "type": "number", "label": "语速"},{"key": "pitch", "type": "number", "label": "音调"}]', 19, 1, NOW(), 1, NOW());

-- 添加阿里百炼流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_AliBLStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_AliBLStreamTTS', 'TTS', 'AliBLStreamTTS', '阿里百炼流式语音合成', 0, 1, '{\"type\": \"alibl_stream\", \"appkey\": \"\", \"output_dir\": \"tmp/\", \"model\": \"cosyvoice-v2\", \"voice\": \"longcheng_v2\", \"format\": \"pcm\", \"sample_rate\": 24000, \"volume\": 50, \"rate\": 1, \"pitch\": 1}', NULL, NULL, 22, NULL, NULL, NULL, NULL);

-- 更新阿里百炼流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1#/api-key',
`remark` = '阿里百炼流式TTS说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key 创建项目并获取appkey
2. 支持实时流式合成，具有较低的延迟
3. 支持多种音色设置和音频参数调整
4. 支持CosyVoice-V3大模型音色，价格实惠(0.4元/万字符)
5. 支持实时调节音量、语速、音调等参数
6. 如果需要使用CosyVoice-V3模型和一些限制类型的音色，需要联系阿里百炼客服申请
' WHERE `id` = 'TTS_AliBLStreamTTS';

-- 添加阿里百炼流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_AliBLStreamTTS';

-- 语音助手
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0001', 'TTS_AliBLStreamTTS', '龙小淳-知性积极女', 'longxiaochun_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0002', 'TTS_AliBLStreamTTS', '龙小夏-沉稳权威女', 'longxiaoxia_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);

-- 直播带货
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0003', 'TTS_AliBLStreamTTS', '龙安燃-活泼质感女', 'longanran', '中文及中英文混合', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0004', 'TTS_AliBLStreamTTS', '龙安宣-经典直播女', 'longanxuan', '中文及中英文混合', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);

-- 社交陪伴
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0005', 'TTS_AliBLStreamTTS', '龙寒-温暖痴情男', 'longhan_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0006', 'TTS_AliBLStreamTTS', '龙颜-温暖春风女', 'longyan_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0007', 'TTS_AliBLStreamTTS', '龙菲菲-甜美矫情女', 'longfeifei_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);

-- 方言
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0008', 'TTS_AliBLStreamTTS', '龙老铁-东北直率男', 'longlaotie_v2', '中文(东北)及中英文混合', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0009', 'TTS_AliBLStreamTTS', '龙嘉怡-知性粤语女', 'longjiayi_v2', '中文(粤语)及中英文混合', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);

-- 童声
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0010', 'TTS_AliBLStreamTTS', '龙杰力豆-阳光顽皮男', 'longjielidou_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0011', 'TTS_AliBLStreamTTS', '龙铃-稚气呆板女', 'longling_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);

-- 诗歌朗诵
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0012', 'TTS_AliBLStreamTTS', '李白-古代诗仙男', 'libai_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);

-- 出海营销
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0013', 'TTS_AliBLStreamTTS', 'loongeva-知性英文女', 'loongeva_v2', '英式英文', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0014', 'TTS_AliBLStreamTTS', 'loongbrian-沉稳英文男', 'loongbrian_v2', '英式英文', NULL, NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0015', 'TTS_AliBLStreamTTS', 'loongkyong-韩语女', 'loongkyong_v2', '韩语', NULL, NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0016', 'TTS_AliBLStreamTTS', 'loongtomoka-日语女', 'loongtomoka_v2', '日语', NULL, NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0017', 'TTS_AliBLStreamTTS', 'loongtomoya-日语男', 'loongtomoya_v2', '日语', NULL, NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);