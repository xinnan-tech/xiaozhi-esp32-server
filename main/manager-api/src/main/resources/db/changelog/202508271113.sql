-- VOSK ASR模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_VoskASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_VoskASR', 'ASR', 'vosk', 'VOSK离线语音识别', '[{"key": "model_path", "type": "string", "label": "模型路径"}, {"key": "output_dir", "type": "string", "label": "输出目录"}]', 11, 1, NOW(), 1, NOW());

-- VOSK ASR模型配置
delete from `ai_model_config` where id = 'ASR_VoskASR';
INSERT INTO `ai_model_config` VALUES ('ASR_VoskASR', 'ASR', 'VoskASR', 'VOSK离线语音识别', 0, 1, '{\"type\": \"vosk\", \"model_path\": \"\", \"output_dir\": \"tmp/\"}', NULL, NULL, 11, NULL, NULL, NULL, NULL);

-- 更新VOSK ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://alphacephei.com/vosk/',
`remark` = 'VOSK ASR配置说明：
1. VOSK是一个离线语音识别库，支持多种语言
2. 需要先下载模型文件：https://alphacephei.com/vosk/models
3. 中文模型推荐使用vosk-model-small-cn-0.22或vosk-model-cn-0.22
4. 完全离线运行，无需网络连接
5. 输出文件保存在tmp/目录
使用步骤：
1. 访问 https://alphacephei.com/vosk/models 下载中文模型
2. 解压模型文件到项目目录下的models/vosk/文件夹
3. 在配置中指定正确的模型路径
4. 注意：VOSK中文模型输出不带标点符号，词与词之间会有空格
' WHERE `id` = 'ASR_VoskASR';