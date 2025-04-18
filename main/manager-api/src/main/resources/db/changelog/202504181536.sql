-- 调整意图识别配置
delete from `ai_model_config` where id = 'Intent_function_call';
INSERT INTO `ai_model_config` VALUES ('Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', 0, 1, '{\"type\": \"function_call\", \"functions\": \"change_role;get_weather;get_news;play_music\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);

-- 增加单台设备每天最多聊天句数
delete from `sys_params` where  id = 105;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (105, 'device_max_output_size', '0', 'number', 1, '单台设备每天最多输出字数，0表示不限制');