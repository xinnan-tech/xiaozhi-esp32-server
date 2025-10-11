-- 添加讯飞流式TTS供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_XunFeiStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_XunFeiStreamTTS', 'TTS', 'xunfei_stream', '讯飞流式语音合成', '[{"key":"app_id","label":"APP_ID","type":"string"},{"key":"api_secret","label":"API_Secret","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key": "volume", "type": "number", "label": "音量"},{"key": "speed", "type": "number", "label": "语速"},{"key": "pitch", "type": "number", "label": "音调"},{"key": "oral_level", "type": "number", "label": "口语化等级"},{"key": "spark_assist", "type": "number", "label": "是否口语化"},{"key": "stop_split", "type": "number", "label": "服务端拆句"},{"key": "remain", "type": "number", "label": "保留书面语"}]', 20, 1, NOW(), 1, NOW());

-- 添加讯飞流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_XunFeiStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_XunFeiStreamTTS', 'TTS', 'XunFeiStreamTTS', '讯飞流式语音合成', 0, 1, '{\"type\": \"xunfei_stream\", \"app_id\": \"\", \"api_secret\": \"\", \"api_key\": \"\", \"output_dir\": \"tmp/\", \"voice\": \"x5_lingxiaoxuan_flow\", \"format\": \"raw\", \"sample_rate\": 24000, \"volume\": 50, \"speed\": 50, \"pitch\": 50, \"oral_level\": \"mid\", \"spark_assist\": 1, \"stop_split\": 0, \"remain\": 0}', NULL, NULL, 23, NULL, NULL, NULL, NULL);

-- 更新讯飞流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.xfyun.cn/app/myapp',
`remark` = '讯飞流式TTS说明：
1. 登录讯飞语音技术平台 https://console.xfyun.cn/app/myapp 创建相关应用
2. 选择需要的服务获取api相关配置 https://console.xfyun.cn/services/uts
3. 为需要使用的应用(APPID)购买相关服务 例如：超拟人合成 https://console.xfyun.cn/services/uts
5. 支持实时双流式通信，具有较低的延迟
6. 支持口语化设置和音频参数调整 注意：V5音色不支持相关口语化配置
7. 支持实时调节音量、语速、音调等参数
' WHERE `id` = 'TTS_XunFeiStreamTTS';

-- 添加讯飞流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_XunFeiStreamTTS';

-- 基础角色
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0001', 'TTS_XunFeiStreamTTS', '聆小璇', 'x5_lingxiaoxuan_flow', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0002', 'TTS_XunFeiStreamTTS', '聆飞逸', 'x5_lingfeiyi_flow', '中文', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0003', 'TTS_XunFeiStreamTTS', '聆小玥', 'x5_lingxiaoyue_flow', '中文', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0004', 'TTS_XunFeiStreamTTS', '聆玉昭', 'x5_lingyuzhao_flow', '中文', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0005', 'TTS_XunFeiStreamTTS', '聆玉言', 'x5_lingyuyan_flow', '中文', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);

-- 需要添加对应的角色音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0006', 'TTS_XunFeiStreamTTS', '聆飞哲', 'x4_lingfeizhe_oral', '中文', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0007', 'TTS_XunFeiStreamTTS', '聆小璃', 'x4_lingxiaoli_oral', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0008', 'TTS_XunFeiStreamTTS', '聆小糖', 'x5_lingxiaotang_flow', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0009', 'TTS_XunFeiStreamTTS', '聆小琪', 'x4_lingxiaoqi_oral', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0010', 'TTS_XunFeiStreamTTS', '聆佑佑-童年女声', 'x4_lingyouyou_oral', '中文', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0011', 'TTS_XunFeiStreamTTS', '子津', 'x4_zijin_oral', '天津话', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0012', 'TTS_XunFeiStreamTTS', '子阳', 'x4_ziyang_oral', '东北话', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0013', 'TTS_XunFeiStreamTTS', 'Grant', 'x5_EnUs_Grant_flow', '英文', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0014', 'TTS_XunFeiStreamTTS', 'Lila', 'x5_EnUs_Lila_flow', '英文', NULL, NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
