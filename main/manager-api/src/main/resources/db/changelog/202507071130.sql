-- 添加阿里云流式ASR供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_AliyunStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_AliyunStreamASR', 'ASR', 'aliyun_stream', '阿里云语音识别(流式)', '[{"key":"appkey","label":"应用AppKey","type":"string"},{"key":"token","label":"临时Token","type":"string"},{"key":"access_key_id","label":"AccessKey ID","type":"string"},{"key":"access_key_secret","label":"AccessKey Secret","type":"string"},{"key":"host","label":"服务地址","type":"string"},{"key":"max_sentence_silence","label":"断句检测时间","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 6, 1, NOW(), 1, NOW());

-- 添加阿里云流式ASR模型配置
delete from `ai_model_config` where id = 'ASR_AliyunStreamASR';
INSERT INTO `ai_model_config` VALUES ('ASR_AliyunStreamASR', 'ASR', 'AliyunStreamASR', '阿里云语音识别(流式)', 0, 1, '{\"type\": \"aliyun_stream\", \"appkey\": \"\", \"token\": \"\", \"access_key_id\": \"\", \"access_key_secret\": \"\", \"host\": \"nls-gateway-cn-shanghai.aliyuncs.com\", \"max_sentence_silence\": 800, \"output_dir\": \"tmp/\"}', NULL, NULL, 8, NULL, NULL, NULL, NULL);

-- 更新阿里云流式ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云流式ASR配置说明：
1. 阿里云ASR和阿里云(流式)ASR的区别是：阿里云ASR是一次性识别，阿里云(流式)ASR是实时流式识别
2. 流式ASR具有更低的延迟和更好的实时性，适合语音交互场景
3. 需要在阿里云智能语音交互控制台创建应用并获取认证信息
4. 支持中文实时语音识别，支持标点符号预测和逆文本规范化
5. 需要网络连接，输出文件保存在tmp/目录
申请步骤：
1. 访问 https://nls-portal.console.aliyun.com/ 开通智能语音交互服务
2. 访问 https://nls-portal.console.aliyun.com/applist 创建项目并获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取临时token（或配置access_key_id和access_key_secret自动获取）
4. 如需动态token管理，建议配置access_key_id和access_key_secret
5. max_sentence_silence参数控制断句检测时间（毫秒），默认800ms
如需了解更多参数配置，请参考：https://help.aliyun.com/zh/isi/developer-reference/real-time-speech-recognition
' WHERE `id` = 'ASR_AliyunStreamASR';
