delete from `sys_params` where param_code = 'server.mqtt_manager_api';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (119, 'server.mqtt_manager_api', 'null', 'string', 1, 'MQTT网关管理API的地址');
