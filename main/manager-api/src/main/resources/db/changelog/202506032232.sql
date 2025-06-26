-- VLLM模型配置
delete from `ai_model_config` where id = 'VLLM_QwenVLVLLM';
INSERT INTO `ai_model_config` VALUES ('VLLM_QwenVLVLLM', 'VLLM', 'QwenVLVLLM', '千问视觉模型', 0, 1, '{\"type\": \"openai\", \"model_name\": \"qwen2.5-vl-3b-instruct\", \"base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\", \"api_key\": \"你的api_key\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);

-- 更新文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2845564.html&renderType=iframe',
`remark` = '千问视觉模型配置说明：
1. 访问 https://bailian.console.aliyun.com/?tab=model#/api-key
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'VLLM_QwenVLVLLM';

-- 删除参数，这两个参数已挪至python配置文件
delete from `sys_params` where id  in (113,114);
