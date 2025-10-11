delete from `ai_model_config` where id = 'LLM_XunfeiSparkLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_XunfeiSparkLLM', 'LLM', '讯飞星火认知大模型', '讯飞星火认知大模型', 0, 1, '{"type": "openai", "model_name": "generalv3.5", "base_url": "https://spark-api-open.xf-yun.com/v1", "api_password": "你的api_password", "temperature": 0.5, "max_tokens": 2048, "top_p": 1.0, "frequency_penalty": 0.0}', 'https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html', '讯飞星火认知大模型，支持多轮对话、文本生成等功能', 14, NULL, NULL, NULL, NULL);

-- 更新讯飞星火认知大模型配置的说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html',
`remark` = '讯飞星火认知大模型配置说明：
1. 登录讯飞开放平台 https://www.xfyun.cn/，每一个模型对应每一个api_password,更改模型时需要查看对应模型的api_password
2. 创建星火认知大模型应用获取API Password
3. 参数说明：
   - api_password: API Password，在讯飞开放平台创建应用后获得
   - model_name: 模型名称，支持generalv3.5、generalv3等版本
   - base_url: API地址，默认https://spark-api-open.xf-yun.com/v1
   - temperature: 温度参数，控制生成随机性，范围0-1，默认0.5
   - max_tokens: 最大输出token数，默认2048
   - top_p: 核心采样参数，控制词汇多样性，默认1.0
   - frequency_penalty: 频率惩罚，降低重复内容，默认0.0
4. 每一个模型对应每一个api_password,更改模型时需要查看对应模型的api_password。
' WHERE `id` = 'LLM_XunfeiSparkLLM';