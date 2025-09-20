-- Add LiveKit-specific model configurations to support LiveKit agents
-- This migration adds Groq-based models that LiveKit agents can use

-- Add LiveKit LLM Models
-- Groq LLM (Primary for LiveKit)
INSERT INTO `ai_model_config` VALUES ('LLM_LiveKitGroqLLM', 'LLM', 'LiveKitGroqLLM', 'Groq大模型(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "openai/gpt-oss-20b",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "base_url": "https://api.groq.com/openai/v1",
  "temperature": 0.7,
  "max_tokens": 2048,
  "timeout": 15
}',
'https://docs.groq.com/',
'LiveKit专用Groq大语言模型，支持快速推理和流式输出',
100, 1, NOW(), 1, NOW());

-- Alternative Groq models for LiveKit
INSERT INTO `ai_model_config` VALUES ('LLM_LiveKitGroqMixtral', 'LLM', 'LiveKitGroqMixtral', 'Groq Mixtral(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "mixtral-8x7b-32768",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "base_url": "https://api.groq.com/openai/v1",
  "temperature": 0.7,
  "max_tokens": 2048,
  "timeout": 15
}',
'https://docs.groq.com/',
'LiveKit专用Groq Mixtral模型，更强大的推理能力',
101, 1, NOW(), 1, NOW());

-- Add LiveKit TTS Models
-- Groq TTS (Primary for LiveKit)
INSERT INTO `ai_model_config` VALUES ('TTS_LiveKitGroqTTS', 'TTS', 'LiveKitGroqTTS', 'Groq语音合成(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "playai-tts",
  "voice": "Aaliyah-PlayAI",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "output_dir": "tmp/",
  "format": "wav"
}',
'https://docs.groq.com/',
'LiveKit专用Groq语音合成，支持多种音色',
100, 1, NOW(), 1, NOW());

-- Alternative TTS voices for LiveKit
INSERT INTO `ai_model_config` VALUES ('TTS_LiveKitGroqTTS_Female', 'TTS', 'LiveKitGroqTTS_Female', 'Groq女声(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "playai-tts",
  "voice": "Diana-PlayAI",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "output_dir": "tmp/",
  "format": "wav"
}',
'https://docs.groq.com/',
'LiveKit专用Groq女声语音合成',
101, 1, NOW(), 1, NOW());

-- Add LiveKit ASR Models
-- Groq ASR (Primary for LiveKit)
INSERT INTO `ai_model_config` VALUES ('ASR_LiveKitGroqASR', 'ASR', 'LiveKitGroqASR', 'Groq语音识别(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "whisper-large-v3-turbo",
  "language": "en",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "output_dir": "tmp/"
}',
'https://docs.groq.com/',
'LiveKit专用Groq语音识别，基于Whisper模型',
100, 1, NOW(), 1, NOW());

-- Multilingual ASR for LiveKit
INSERT INTO `ai_model_config` VALUES ('ASR_LiveKitGroqASR_Multi', 'ASR', 'LiveKitGroqASR_Multi', 'Groq多语言识别(LiveKit)', 0, 1,
'{
  "type": "groq",
  "provider": "groq",
  "model": "whisper-large-v3",
  "language": "auto",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "output_dir": "tmp/"
}',
'https://docs.groq.com/',
'LiveKit专用Groq多语言语音识别',
101, 1, NOW(), 1, NOW());

-- Add LiveKit VAD Models (reuse existing Silero, but LiveKit-optimized)
INSERT INTO `ai_model_config` VALUES ('VAD_LiveKitSileroVAD', 'VAD', 'LiveKitSileroVAD', 'Silero VAD(LiveKit)', 0, 1,
'{
  "type": "silero",
  "provider": "silero",
  "model_dir": "models/snakers4_silero-vad",
  "threshold": 0.5,
  "min_silence_duration_ms": 700,
  "optimized_for_livekit": true
}',
'https://github.com/snakers4/silero-vad',
'LiveKit优化的Silero语音活动检测',
100, 1, NOW(), 1, NOW());

-- Add LiveKit Memory Models
-- Simple memory for LiveKit
INSERT INTO `ai_model_config` VALUES ('Memory_LiveKitSimple', 'Memory', 'LiveKitSimple', '简单记忆(LiveKit)', 0, 1,
'{
  "type": "simple",
  "provider": "local",
  "max_history": 10,
  "optimized_for_livekit": true
}',
NULL,
'LiveKit专用简单对话记忆',
100, 1, NOW(), 1, NOW());

-- Mem0AI for LiveKit (with LiveKit-specific settings)
INSERT INTO `ai_model_config` VALUES ('Memory_LiveKitMem0AI', 'Memory', 'LiveKitMem0AI', 'Mem0AI记忆(LiveKit)', 0, 1,
'{
  "type": "mem0ai",
  "provider": "mem0ai",
  "api_key": "YOUR_MEM0AI_API_KEY_HERE",
  "optimized_for_livekit": true,
  "session_based": true
}',
'https://mem0.ai/',
'LiveKit专用Mem0AI记忆系统',
101, 1, NOW(), 1, NOW());

-- Add LiveKit Intent Models
-- Function calling for LiveKit
INSERT INTO `ai_model_config` VALUES ('Intent_LiveKitFunctionCall', 'Intent', 'LiveKitFunctionCall', '函数调用(LiveKit)', 0, 1,
'{
  "type": "function_call",
  "provider": "livekit",
  "functions": "get_weather;play_music;control_device",
  "optimized_for_livekit": true
}',
NULL,
'LiveKit专用函数调用意图识别',
100, 1, NOW(), 1, NOW());

-- Add LiveKit Agent Template
-- Default LiveKit agent configuration (22 columns total)
INSERT INTO `ai_agent_template` VALUES (
  'AGENT_TEMPLATE_LIVEKIT_DEFAULT',                     -- 1. id
  'livekit_default',                                    -- 2. agent_code
  'LiveKit默认智能体',                                    -- 3. agent_name
  'ASR_LiveKitGroqASR',                                -- 4. asr_model_id
  'VAD_LiveKitSileroVAD',                              -- 5. vad_model_id
  'LLM_LiveKitGroqLLM',                                -- 6. llm_model_id
  NULL,                                                -- 7. vllm_model_id
  'TTS_LiveKitGroqTTS',                                -- 8. tts_model_id
  NULL,                                                -- 9. tts_voice_id
  'Memory_LiveKitSimple',                              -- 10. mem_model_id
  'Intent_LiveKitFunctionCall',                        -- 11. intent_model_id
  'You are a helpful AI assistant powered by LiveKit real-time communication. Respond naturally and keep conversations engaging.', -- 12. system_prompt
  NULL,                                                -- 13. summary_memory
  1,                                                   -- 14. chat_history_conf
  'en',                                                -- 15. lang_code
  'English',                                           -- 16. language
  1,                                                   -- 17. sort
  1,                                                   -- 18. is_visible
  1,                                                   -- 19. creator
  NOW(),                                               -- 20. created_at
  1,                                                   -- 21. updater
  NOW()                                                -- 22. updated_at
);

-- Add LiveKit Agent Template (Chinese)
INSERT INTO `ai_agent_template` VALUES (
  'AGENT_TEMPLATE_LIVEKIT_CHINESE',                     -- 1. id
  'livekit_chinese',                                    -- 2. agent_code
  'LiveKit中文智能体',                                    -- 3. agent_name
  'ASR_LiveKitGroqASR_Multi',                          -- 4. asr_model_id
  'VAD_LiveKitSileroVAD',                              -- 5. vad_model_id
  'LLM_LiveKitGroqLLM',                                -- 6. llm_model_id
  NULL,                                                -- 7. vllm_model_id
  'TTS_LiveKitGroqTTS_Female',                         -- 8. tts_model_id
  NULL,                                                -- 9. tts_voice_id
  'Memory_LiveKitMem0AI',                              -- 10. mem_model_id
  'Intent_LiveKitFunctionCall',                        -- 11. intent_model_id
  '你是一个由LiveKit实时通信技术驱动的AI助手。请自然地回应，让对话保持有趣和富有参与性。', -- 12. system_prompt
  NULL,                                                -- 13. summary_memory
  1,                                                   -- 14. chat_history_conf
  'zh',                                                -- 15. lang_code
  '中文',                                               -- 16. language
  2,                                                   -- 17. sort
  1,                                                   -- 18. is_visible
  1,                                                   -- 19. creator
  NOW(),                                               -- 20. created_at
  1,                                                   -- 21. updater
  NOW()                                                -- 22. updated_at
);