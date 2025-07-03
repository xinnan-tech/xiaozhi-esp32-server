ALTER TABLE `ai_tts_voice`
ADD COLUMN `reference_audio` VARCHAR(500) DEFAULT NULL COMMENT '参考音频路径' AFTER `remark`,
ADD COLUMN `reference_text` VARCHAR(500) DEFAULT NULL COMMENT '参考文本' AFTER `reference_audio`;
