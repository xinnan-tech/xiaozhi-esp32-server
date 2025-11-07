-- 添加 ElevenLabs 和 Cartesia TTS 供应器和模型配置

-- ==================== ElevenLabs TTS ====================

-- 添加 ElevenLabs TTS 供应器
DELETE FROM `ai_model_provider` WHERE id = 'TTS_ElevenLabs';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('TTS_ElevenLabs', 'TTS', 'elevenlabs', 'ElevenLabs TTS', '[{"key":"api_key","label":"API Key","type":"string"},{"key":"voice_id","label":"Voice ID","type":"string"},{"key":"model","label":"Model","type":"string"},{"key":"output_format","label":"Output Format","type":"string"},{"key":"stability","label":"Stability","type":"number"},{"key":"similarity_boost","label":"Similarity Boost","type":"number"},{"key":"style","label":"Style","type":"number"},{"key":"use_speaker_boost","label":"Use Speaker Boost","type":"string"},{"key":"optimize_streaming_latency","label":"Optimize Streaming Latency","type":"number"},{"key":"output_dir","label":"Output Directory","type":"string"}]', 21, 1, NOW(), 1, NOW());

-- 添加 ElevenLabs TTS 模型配置
DELETE FROM `ai_model_config` WHERE id = 'TTS_ElevenLabs';
INSERT INTO `ai_model_config` VALUES (
  'TTS_ElevenLabs', 
  'TTS', 
  'ElevenLabs', 
  'ElevenLabs TTS', 
  0, 
  1, 
  '{\"type\": \"elevenlabs\", \"api_key\": \"\", \"voice_id\": \"21m00Tcm4TlvDq8ikWAM\", \"model\": \"eleven_multilingual_v2\", \"output_format\": \"pcm_16000\", \"stability\": 0.5, \"similarity_boost\": 0.75, \"style\": 0.0, \"use_speaker_boost\": true, \"optimize_streaming_latency\": 3, \"output_dir\": \"tmp/\"}', 
  'https://elevenlabs.io/docs/introduction',
  'ElevenLabs TTS 配置说明：\n1. ElevenLabs 提供高质量、情感丰富的语音合成服务\n2. 支持多语言（包括英文、中文等）和声音克隆功能\n3. 使用官方 Python SDK，延迟低、质量高\n4. API Key 获取：访问 https://elevenlabs.io/ 注册并获取\n5. Voice ID 可在 ElevenLabs 控制台中找到预设音色或创建自定义音色\n6. Model 推荐使用 eleven_multilingual_v2（多语言）或 eleven_turbo_v2（低延迟）\n7. Stability (0-1): 控制语音稳定性，越高越稳定但变化少\n8. Similarity Boost (0-1): 控制与原音色的相似度\n9. Style (0-1): 控制语音风格强度\n10. Optimize Streaming Latency (0-4): 优化流式延迟，推荐 2-3',
  23, 
  NULL, 
  NULL, 
  NULL, 
  NULL
);

-- 添加 ElevenLabs 音色配置
DELETE FROM `ai_tts_voice` WHERE id IN ('TTS_ElevenLabs0001', 'TTS_ElevenLabs0002', 'TTS_ElevenLabs0003', 'TTS_ElevenLabs0004');
INSERT INTO `ai_tts_voice` VALUES ('TTS_ElevenLabs0001', 'TTS_ElevenLabs', 'Rachel - Female', '21m00Tcm4TlvDq8ikWAM', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_ElevenLabs0002', 'TTS_ElevenLabs', 'Drew - Male', '29vD33N1CtxCmqQRPOHJ', 'English', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_ElevenLabs0003', 'TTS_ElevenLabs', 'Clyde - Male', '2EiwWnXFnvU5JabPnv8n', 'English', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_ElevenLabs0004', 'TTS_ElevenLabs', 'Bella - Female', 'EXAVITQu4vr4xnSDxMaL', 'English', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);

-- ==================== Cartesia TTS ====================

-- 添加 Cartesia TTS 供应器
DELETE FROM `ai_model_provider` WHERE id = 'TTS_Cartesia';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('TTS_Cartesia', 'TTS', 'cartesia', 'Cartesia TTS', '[{"key":"api_key","label":"API Key","type":"string"},{"key":"voice_id","label":"Voice ID","type":"string"},{"key":"model","label":"Model","type":"string"},{"key":"language","label":"Language","type":"string"},{"key":"encoding","label":"Encoding","type":"string"},{"key":"sample_rate","label":"Sample Rate","type":"number"},{"key":"output_dir","label":"Output Directory","type":"string"}]', 22, 1, NOW(), 1, NOW());

-- 添加 Cartesia TTS 模型配置
DELETE FROM `ai_model_config` WHERE id = 'TTS_Cartesia';
INSERT INTO `ai_model_config` VALUES (
  'TTS_Cartesia', 
  'TTS', 
  'Cartesia', 
  'Cartesia TTS', 
  0, 
  1, 
  '{\"type\": \"cartesia\", \"api_key\": \"\", \"voice_id\": \"a0e99841-438c-4a64-b679-ae501e7d6091\", \"model\": \"sonic-3\", \"language\": \"en\", \"encoding\": \"pcm_s16le\", \"sample_rate\": 24000, \"output_dir\": \"tmp/\"}', 
  'https://docs.cartesia.ai/',
  'Cartesia TTS 配置说明：\n1. Cartesia 提供超低延迟的流式语音合成服务\n2. 使用官方 Python SDK，首包延迟极低（通常 < 200ms）\n3. 支持多种语言和声音（英语、西班牙语、法语、德语、中文等）\n4. API Key 获取：访问 https://cartesia.ai/ 注册并获取\n5. Voice ID 可在 Cartesia 控制台查看预设音色\n6. Model 选项：sonic-english（英语）、sonic-multilingual（多语言）\n7. Encoding: pcm_s16le（推荐）、pcm_mulaw 等\n8. Sample Rate: 8000/16000/24000/44100（推荐 24000）\n9. 特别适合需要实时交互的场景（如语音助手、客服）',
  24, 
  NULL, 
  NULL, 
  NULL, 
  NULL
);

-- 添加 Cartesia 音色配置
DELETE FROM `ai_tts_voice` WHERE id IN ('TTS_Cartesia0001', 'TTS_Cartesia0002', 'TTS_Cartesia0003', 'TTS_Cartesia0004');
INSERT INTO `ai_tts_voice` VALUES ('TTS_Cartesia0001', 'TTS_Cartesia', 'Barbershop Man', 'a0e99841-438c-4a64-b679-ae501e7d6091', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_Cartesia0002', 'TTS_Cartesia', 'Kentucky Man', '41534e16-2966-4c6b-9670-111411def906', 'English', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_Cartesia0003', 'TTS_Cartesia', 'British Lady', '79a125e8-cd45-4c13-8a67-188112f4dd22', 'English', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_Cartesia0004', 'TTS_Cartesia', 'Friendly Reader', '69267136-1bdc-412f-ad78-0caad210fb40', 'English', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);

