-- 添加SM2国密算法密钥参数
-- 用于服务器端SM2加密解密功能

-- 添加SM2密钥参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES 
(120, 'server.public_key', '', 'string', 1, '服务器SM2公钥'),
(121, 'server.private_key', '', 'string', 1, '服务器SM2私钥');