-- Add OpenAI TTS and Gemini TTS providers to ai_model_provider table
-- This file adds the provider definitions needed for the dashboard dropdown
-- -----------------------------------------------------------------------

-- Add OpenAI TTS provider definition
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_TTS_OpenAITTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_OpenAITTS', 'TTS', 'openai', 'OpenAI TTS语音合成', '[{"key":"api_key","label":"API密钥","type":"string","required":true},{"key":"api_url","label":"API地址","type":"string","required":true},{"key":"model","label":"模型","type":"string","required":true},{"key":"voice","label":"音色","type":"string","required":true},{"key":"speed","label":"语速","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 18, 1, NOW(), 1, NOW());

-- Add Gemini TTS provider definition  
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_TTS_GeminiTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_GeminiTTS', 'TTS', 'gemini', 'Google Gemini TTS语音合成', '[{"key":"api_key","label":"API密钥","type":"string","required":true},{"key":"api_url","label":"API地址","type":"string","required":true},{"key":"model","label":"模型","type":"string","required":true},{"key":"voice","label":"音色","type":"string","required":true},{"key":"language","label":"语言","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 19, 1, NOW(), 1, NOW());