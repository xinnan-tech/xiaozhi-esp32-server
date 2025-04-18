delete from `ai_model_config` where id = 'Intent_function_call';
INSERT INTO `ai_model_config` VALUES ('Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', 0, 1, '{\"type\": \"function_call\", \"functions\": \"change_role;get_weather;get_news;play_music\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);
