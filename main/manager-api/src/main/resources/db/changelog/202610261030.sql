-- 添加MCP接入点附带说话人身份的开关参数配置
delete from `sys_params` where param_code = 'mcp_forward_speaker';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (313, 'mcp_forward_speaker', 'true', 'boolean', 1, '是否随MCP调用附带说话人身份');
