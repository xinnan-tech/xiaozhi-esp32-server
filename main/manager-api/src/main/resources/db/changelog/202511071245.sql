-- Add Deepgram TTS Provider and Model Configuration

-- ==================== Deepgram TTS ====================

-- Add Deepgram TTS Provider
DELETE FROM `ai_model_provider` WHERE id = 'TTS_Deepgram';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('TTS_Deepgram', 'TTS', 'deepgram', 'Deepgram TTS', '[{"key":"api_key","label":"API Key","type":"string"},{"key":"model","label":"Model","type":"string"}]', 20, 1, NOW(), 1, NOW());

-- Add Deepgram TTS Model Configuration
DELETE FROM `ai_model_config` WHERE id = 'TTS_Deepgram';
INSERT INTO `ai_model_config` (
  `id`,
  `model_type`,
  `model_code`,
  `model_name`,
  `is_default`,
  `is_enabled`,
  `config_json`,
  `doc_link`,
  `remark`,
  `sort`,
  `creator`,
  `create_date`,
  `updater`,
  `update_date`
) VALUES (
  'TTS_Deepgram',
  'TTS',
  'Deepgram',
  'Deepgram TTS',
  0,
  1,
  '{"type": "deepgram", "api_key": "", "model": "aura-2-thalia-en"}',
  'https://developers.deepgram.com/docs/text-to-speech',
  'Deepgram TTS Configuration:\n1. Deepgram provides high-quality, low-latency AI text-to-speech service\n2. Uses official Deepgram Python SDK (deepgram-sdk)\n3. Supports multiple languages and Aura 2 voice models\n4. API Key: Register at https://console.deepgram.com/ to get your API key\n5. Model: Deepgram voice models directly specify the voice (e.g., aura-2-thalia-en, aura-2-stella-en, aura-2-orion-en)\n6. Available Models:\n   - Female: aura-2-asteria-en, aura-2-luna-en, aura-2-stella-en, aura-2-athena-en\n   - Male: aura-2-orion-en, aura-2-arcas-en, aura-2-perseus-en, aura-2-zeus-en\n7. Features: Natural voices, multi-language support, low latency\n8. Perfect for real-time voice applications and conversational AI',
  22,
  NULL,
  NULL,
  NULL,
  NULL
);

