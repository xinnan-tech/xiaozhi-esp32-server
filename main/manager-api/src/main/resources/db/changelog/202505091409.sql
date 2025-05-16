-- 更新intent_llmM供应器
update `ai_model_provider` set fields =  '[{"key":"llm","label":"LLM模型","type":"string"},{"key":"functions","label":"函数列表","type":"dict","dict_name":"functions"}]' where  id = 'SYSTEM_Intent_intent_llm';
-- 更新ChatGLMLLM的意图识别配置
update `ai_model_config` set config_json =  '{\"type\": \"intent_llm\", \"llm\": \"LLM_ChatGLMLLM\", \"functions\": \"get_weather;get_news_from_newsnow;play_music\"}' where  id = 'Intent_intent_llm';
-- 更新函数调用意图识别配置
UPDATE `ai_model_config` SET config_json = REPLACE(config_json, ';get_news;', ';get_news_from_newsnow;') WHERE id = 'Intent_function_call';
