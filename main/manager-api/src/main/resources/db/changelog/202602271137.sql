-- 更新腾讯TTS供应器配置，增加speed、volume和format参数
UPDATE `ai_model_provider`
SET fields = '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"speed","label":"语速","type":"number"},{"key":"volume","label":"音量","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice","label":"音色ID","type":"string"},{"key":"region","label":"区域","type":"string"}]'
WHERE id = 'SYSTEM_TTS_TencentTTS';

-- 更新腾讯TTS模型配置，增加speed和volume参数，补充参数说明
UPDATE `ai_model_config` SET 
    `config_json` = JSON_SET(`config_json`, '$.speed', 0, '$.volume', 0),
    `remark` = '腾讯TTS配置说明：
1. 需要在腾讯云平台开通智能语音交互服务
2. 支持多种音色，当前配置使用101001
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.cloud.tencent.com/cam/capi 获取密钥
2. 访问 https://console.cloud.tencent.com/tts/resourcebundle 领取免费资源
3. 创建新应用
4. 获取appid、secret_id和secret_key
5. 填入配置文件中
音频参数：
- format: 音频格式，支持pcm、wav、mp3
- speed: 语速，范围-2~6，默认0
- volume: 音量，范围-10~10，默认0'
WHERE `id` = 'TTS_TencentTTS';

-- 更新CozeCnTTS供应器配置，增加speed和loudness_rate参数
UPDATE `ai_model_provider`
SET fields = '[{"key":"voice","label":"音色","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"speed","label":"语速","type":"number"},{"key":"loudness_rate","label":"音量增益","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"response_format","label":"响应格式","type":"string"}]'
WHERE id = 'SYSTEM_TTS_cozecn';

-- 更新CozeCnTTS模型配置，增加speed和loudness_rate参数，补充参数说明
UPDATE `ai_model_config` SET 
    `config_json` = JSON_SET(`config_json`, '$.speed', 1, '$.loudness_rate', 0),
    `remark` = 'Coze中文语音合成配置说明：
1. 访问 https://www.coze.cn/ 注册并登录
2. 创建应用并获取access_token
3. 选择合适的音色ID
音频参数：
- response_format: 音频格式，支持pcm、wav、mp3
- speed: 语速，范围0.5~2，默认1
- loudness_rate: 音量增益，范围-50~100，默认0'
WHERE `id` = 'TTS_CozeCnTTS';
