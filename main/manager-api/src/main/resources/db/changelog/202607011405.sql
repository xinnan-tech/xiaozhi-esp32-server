-- Add language configuration for local FunASR ASR.
UPDATE `ai_model_provider`
SET `fields` = '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"language","label":"识别语言","type":"string","default":"auto"}]'
WHERE `id` = 'SYSTEM_ASR_FunASR';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.language', 'auto')
WHERE `id` = 'ASR_FunASR'
AND JSON_EXTRACT(`config_json`, '$.language') IS NULL;

-- Update the FunASR local model configuration description to mention the language option.
UPDATE `ai_model_config`
SET `remark` = 'FunASR本地模型配置说明：
1. 需要下载模型文件到xiaozhi-server/models/SenseVoiceSmall目录
2. 支持中日韩粤语音识别
3. 本地推理，无需网络连接
4. 待识别文件保存在tmp/目录
5. “识别语言”字段控制识别语种：auto = 自动检测；如需限定只识别中文可设为 zh（en=英语、ja=日语、ko=韩语、yue=粤语）。'
WHERE `id` = 'ASR_FunASR';
