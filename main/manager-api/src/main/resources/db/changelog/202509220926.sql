-- 添加讯飞流式语音识别服务配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_XunfeiStream';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_XunfeiStream', 'ASR', 'xunfei_stream', '讯飞流式语音识别', '[{"key":"app_id","label":"应用ID","type":"string"},{"key":"api_key","label":"API_KEY","type":"password"},{"key":"api_secret","label":"API_SECRET","type":"password"},{"key":"domain","label":"识别领域","type":"string"},{"key":"language","label":"识别语言","type":"string"},{"key":"accent","label":"方言","type":"string"},{"key":"dwa","label":"动态修正","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 18, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'ASR_XunfeiStream';
INSERT INTO `ai_model_config` VALUES ('ASR_XunfeiStream', 'ASR', '讯飞流式语音识别', '讯飞流式语音识别服务', 0, 1, '{"type": "xunfei_stream", "app_id": "", "api_key": "", "api_secret": "", "domain": "slm", "language": "zh_cn", "accent": "mandarin", "dwa": "wpgs", "output_dir": "tmp/"}', 'https://www.xfyun.cn/doc/spark/spark_zh_iat.html', '支持实时流式语音识别，适用于中文普通话及多种方言识别', 21, NULL, NULL, NULL, NULL);

-- 更新讯飞流式语音识别模型配置的说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.xfyun.cn/doc/spark/spark_zh_iat.html',
`remark` = '讯飞流式语音识别配置说明：
1. 登录讯飞开放平台 https://www.xfyun.cn/
2. 创建语音识别应用获取APPID、APISecret、APIKey
3. 参数说明：
   - app_id: 应用ID，在讯飞开放平台创建应用后获得
   - api_key: API密钥，用于接口鉴权
   - api_secret: API密钥，用于生成签名
   - domain: 识别领域，默认slm（智能化语音转写）
   - language: 识别语言，默认zh_cn（中文）
   - accent: 方言类型，默认mandarin（普通话），支持cantonese（粤语）等
   - dwa: 动态修正，默认wpgs（开启动态修正）
   - output_dir: 音频文件输出目录，默认tmp/
4. 支持实时流式识别，适用于实时语音交互场景
5. 支持多种方言和语言识别
' WHERE `id` = 'ASR_XunfeiStream';