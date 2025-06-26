-- LLM意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = 'LLM意图识别配置说明：
1. 使用独立的LLM进行意图识别
2. 默认使用selected_module.LLM的模型
3. 可以配置使用独立的LLM（如免费的ChatGLMLLM）
4. 通用性强，但会增加处理时间
配置说明：
1. 在llm字段中指定使用的LLM模型
2. 如果不指定，则使用selected_module.LLM的模型' WHERE `id` = 'Intent_intent_llm';

-- 函数调用意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '函数调用意图识别配置说明：
1. 使用LLM的function_call功能进行意图识别
2. 需要所选择的LLM支持function_call
3. 按需调用工具，处理速度快' WHERE `id` = 'Intent_function_call';