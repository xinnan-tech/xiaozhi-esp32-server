-- 阿里百炼流式 TTS 支持业务空间 WebSocket 地址

UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY(
    JSON_OBJECT('key', 'api_key', 'type', 'string', 'label', 'API密钥'),
    JSON_OBJECT(
        'key', 'ws_url',
        'type', 'string',
        'label', 'WebSocket地址（含Workspace ID）',
        'default', 'wss://dashscope.aliyuncs.com/api-ws/v1/inference/'
    ),
    JSON_OBJECT('key', 'output_dir', 'type', 'string', 'label', '输出目录'),
    JSON_OBJECT('key', 'model', 'type', 'string', 'label', '模型'),
    JSON_OBJECT('key', 'voice', 'type', 'string', 'label', '音色'),
    JSON_OBJECT('key', 'format', 'type', 'string', 'label', '音频格式'),
    JSON_OBJECT('key', 'sample_rate', 'type', 'number', 'label', '采样率'),
    JSON_OBJECT('key', 'volume', 'type', 'number', 'label', '音量'),
    JSON_OBJECT('key', 'rate', 'type', 'number', 'label', '语速'),
    JSON_OBJECT('key', 'pitch', 'type', 'number', 'label', '音调')
)
WHERE `id` = 'SYSTEM_TTS_AliBLStreamTTS';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(
    `config_json`,
    '$.ws_url',
    COALESCE(
        NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.ws_url')), ''),
        'wss://dashscope.aliyuncs.com/api-ws/v1/inference/'
    )
)
WHERE `id` = 'TTS_AliBLStreamTTS';

UPDATE `ai_model_config`
SET `remark` = '阿里百炼流式 TTS 配置说明：
1. API密钥填写当前业务空间可用的 DashScope API Key
2. 公有模式可使用 wss://dashscope.aliyuncs.com/api-ws/v1/inference/
3. 华北2（北京）业务空间填写 wss://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference
4. 新加坡业务空间填写 wss://<WorkspaceId>.ap-southeast-1.maas.aliyuncs.com/api-ws/v1/inference
5. 将 <WorkspaceId> 替换为真实业务空间 ID；仅支持阿里云官方 WSS 推理地址
6. 支持 CosyVoice 流式合成及音量、语速、音调配置'
WHERE `id` = 'TTS_AliBLStreamTTS';
