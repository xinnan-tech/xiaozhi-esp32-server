update ai_agent_template set system_prompt = replace(system_prompt, '我是', '你是');

delete from sys_params where id in (500,501,402);
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (500, 'end_prompt.enable', 'true', 'boolean', 1, '是否开启结束语');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (501, 'end_prompt.prompt', '请你以“时间过得真快”未来头，用富有感情、依依不舍的话来结束这场对话吧！', 'string', 1, '结束提示词');

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (402, 'plugins.get_weather.api_host', 'mj7p3y7naa.re.qweatherapi.com', 'string', 1, '开发者apihost');