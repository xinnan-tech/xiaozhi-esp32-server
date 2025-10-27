-- 添加设备ID加密密钥参数
-- 用于MCP工具调用时加密设备ID，防止MAC地址被拦截和滥用

delete from `sys_params` where param_code = 'server.device_id_encrypt_key';
-- 添加device_id_encrypt_key参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES
(122, 'server.device_id_encrypt_key', '你的mac地址加密密钥', 'string', 1, '设备ID加密密钥，用于MCP工具调用时加密设备MAC地址');
