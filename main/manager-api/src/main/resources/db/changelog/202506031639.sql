-- VLLM模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_DoubaoStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_DoubaoStreamASR', 'ASR', 'doubao_stream', '火山引擎语音识别(流式)', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 3, 1, NOW(), 1, NOW());


-- VLLM模型配置
delete from `ai_model_config` where id = 'ASR_DoubaoStreamASR';
INSERT INTO `ai_model_config` VALUES ('ASR_DoubaoStreamASR', 'ASR', 'DoubaoStreamASR', '豆包语音识别(流式)', 0, 1, '{\"type\": \"doubao_stream\", \"appid\": \"\", \"access_token\": \"\", \"cluster\": \"volcengine_input_common\", \"output_dir\": \"tmp/\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);


-- 更新豆包ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 豆包ASR和豆包(流式)ASR的区别是：豆包ASR是按次收费，豆包(流式)ASR是按时收费
2. 一般来说按次收费的更便宜，但是豆包(流式)ASR使用了大模型技术，效果更好
3. 需要在火山引擎控制台创建应用并获取appid和access_token
4. 支持中文语音识别
5. 需要网络连接
6. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoASR';

UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 豆包ASR和豆包(流式)ASR的区别是：豆包ASR是按次收费，豆包(流式)ASR是按时收费
2. 一般来说按次收费的更便宜，但是豆包(流式)ASR使用了大模型技术，效果更好
3. 需要在火山引擎控制台创建应用并获取appid和access_token
4. 支持中文语音识别
5. 需要网络连接
6. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoStreamASR';
