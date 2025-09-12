-- 添加声纹识别相似度阈值参数配置
delete from `sys_params` where id = 115;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (115, 'server.voiceprint_similarity_threshold', '0.4', 'string', 1, '声纹识别相似度阈值，范围0.0-1.0，默认0.4，数值越高越严格');
