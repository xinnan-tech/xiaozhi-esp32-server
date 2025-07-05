delete from `sys_params` where id = 108;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (108, 'server.mqtt_gateway', 'null', 'string', 1, 'mqtt gateway 配置');

delete from `sys_params` where id = 109;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (109, 'server.udp_gateway', 'null', 'string', 1, 'udp gateway 配置');