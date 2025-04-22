-- 删除server.ip和server.port，改成在xiaozhi-server中配置，方便运行多个websocket
delete from `sys_params` where id = 100;
delete from `sys_params` where id = 101;

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (106, 'server.websocket', 'null', 'string', 1, 'websocket地址，多个用;分隔');

