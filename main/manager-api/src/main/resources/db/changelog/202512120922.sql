-- liquibase formatted sql

-- changeset xiaozhi:202512120922
-- 添加 AnimalSound 动物叫声 TTS 供应器
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_TTS_AnimalSound';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) 
VALUES ('SYSTEM_TTS_AnimalSound', 'TTS', 'animal_sound', '动物叫声', 
'[{"key":"base_path","label":"音频文件目录","type":"string"},{"key":"emotion_files","label":"情绪音频映射","type":"dict","dict_name":"emotion_files"},{"key":"default_file","label":"默认音频文件","type":"string"},{"key":"emotion_keywords","label":"情绪关键词映射","type":"dict","dict_name":"emotion_keywords"}]', 
24, 1, NOW(), 1, NOW());

-- 添加 AnimalSound TTS 模型配置
DELETE FROM `ai_model_config` WHERE id = 'TTS_AnimalSound';
INSERT INTO `ai_model_config` VALUES ('TTS_AnimalSound', 'TTS', 'AnimalSound', '动物叫声', 0, 1, 
'{"type": "animal_sound", "base_path": "config/assets/animal_sounds", "emotion_files": {"happy": "cat_happy.wav", "sad": "cat_sad.wav", "angry": "cat_angry.wav", "afraid": "cat_afraid.wav", "helpless": "cat_helpless.wav", "coquetry": "cat_coquetry.wav", "default": "cat_neutral.wav"}, "emotion_keywords": {"happy": ["开心", "高兴", "快乐", "喜悦"], "sad": ["悲伤", "难过", "伤心", "沮丧"], "angry": ["生气", "愤怒", "气愤"], "afraid": ["害怕", "恐惧", "紧张"], "helpless": ["无奈", "唉", "叹气"], "coquetry": ["撒娇", "卖萌", "黏人"]}}', 
NULL, NULL, 24, NULL, NULL, NULL, NULL);

-- 更新 AnimalSound 配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/animal-sound-mode.md',
`remark` = '动物叫声模式配置说明：
1. 此模式用于模仿动物和人的交互，根据LLM输出的情绪标签播放对应的动物叫声音频。
2. 需要在 base_path 目录下放置对应的音频文件（建议 16k/mono 的 wav 或 mp3 格式）。
3. 支持的情绪类型：开心、悲伤、生气、害怕、无奈、撒娇。
4. 如果LLM输出中包含情绪关键词，会自动匹配对应的音频文件。
5. 如果找不到对应情绪的音频，会使用 default 音频文件。
6. 详细使用说明请参考文档：docs/animal-sound-mode.md
' WHERE `id` = 'TTS_AnimalSound';

-- 添加默认音色（虽然动物叫声不需要音色，但为了兼容性添加）
DELETE FROM `ai_tts_voice` WHERE tts_model_id = 'TTS_AnimalSound';
INSERT INTO `ai_tts_voice` VALUES ('TTS_AnimalSound_0000', 'TTS_AnimalSound', '默认', 'default', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);

