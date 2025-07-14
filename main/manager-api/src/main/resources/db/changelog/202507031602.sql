-- 添加声纹接口地址参数配置
delete from `sys_params` where id = 114;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (114, 'server.voice_print', 'null', 'string', 1, '声纹接口地址');