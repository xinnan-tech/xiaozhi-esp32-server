-- 添加手机短信注册功能的需要的参数
delete from sys_params where id in (108, 109, 110, 111, 112, 113, 114, 115);
delete from sys_params where id in (610, 611, 612, 613);
INSERT INTO sys_params
(id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date)
    VALUES
(108, 'server.name', 'xiaozhi-esp32-server', 'string', 1, '系统名称', NULL, NULL, NULL, NULL),
(109, 'server.beian_icp_num', 'null', 'string', 1, 'icp备案号，填写null则不设置', NULL, NULL, NULL, NULL),
(110, 'server.beian_ga_num', 'null', 'string', 1, '公安备案号，填写null则不设置', NULL, NULL, NULL, NULL),
(111, 'server.enable_mobile_register', 'false', 'boolean', 1, '是否开启手机注册', NULL, NULL, NULL, NULL),
(112, 'server.sms_max_send_count', '10', 'number', 1, '单号码单日最大短信发送条数', NULL, NULL, NULL, NULL),
(610, 'aliyun.sms.access_key_id', '', 'string', 1, '阿里云平台access_key', NULL, NULL, NULL, NULL),
(611, 'aliyun.sms.access_key_secret', '', 'string', 1, '阿里云平台access_key_secret', NULL, NULL, NULL, NULL),
(612, 'aliyun.sms.sign_name', '', 'string', 1, '阿里云短信签名', NULL, NULL, NULL, NULL),
(613, 'aliyun.sms.sms_code_template_code', '', 'string', 1, '阿里云短信模板', NULL, NULL, NULL, NULL);

update sys_params set remark = '是否允许管理员以外的人注册' where param_code = 'server.allow_user_register';

-- 增加手机区域字典
-- 插入固件类型字典类型
delete from `sys_dict_type` where `id` = 102;
INSERT INTO `sys_dict_type` (`id`, `dict_type`, `dict_name`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(102, 'MOBILE_AREA', '手机区域', '手机区域字典', 0, 1, NOW(), 1, NOW());

-- 插入固件类型字典数据
delete from `sys_dict_data` where `dict_type_id` = 102;
INSERT INTO `sys_dict_data` (`id`, `dict_type_id`, `dict_label`, `dict_value`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(102001, 102, '中国大陆', '+86', '中国大陆', 1, 1, NOW(), 1, NOW()),
(102002, 102, '中国香港', '+852', '中国香港', 2, 1, NOW(), 1, NOW()),
(102003, 102, '中国澳门', '+853', '中国澳门', 3, 1, NOW(), 1, NOW()),
(102004, 102, '中国台湾', '+886', '中国台湾', 4, 1, NOW(), 1, NOW()),
(102005, 102, '美国/加拿大', '+1', '美国/加拿大', 5, 1, NOW(), 1, NOW()),
(102006, 102, '英国', '+44', '英国', 6, 1, NOW(), 1, NOW()),
(102007, 102, '法国', '+33', '法国', 7, 1, NOW(), 1, NOW()),
(102008, 102, '意大利', '+39', '意大利', 8, 1, NOW(), 1, NOW()),
(102009, 102, '德国', '+49', '德国', 9, 1, NOW(), 1, NOW()),
(102010, 102, '波兰', '+48', '波兰', 10, 1, NOW(), 1, NOW()),
(102011, 102, '瑞士', '+41', '瑞士', 11, 1, NOW(), 1, NOW()),
(102012, 102, '西班牙', '+34', '西班牙', 12, 1, NOW(), 1, NOW()),
(102013, 102, '丹麦', '+45', '丹麦', 13, 1, NOW(), 1, NOW()),
(102014, 102, '马来西亚', '+60', '马来西亚', 14, 1, NOW(), 1, NOW()),
(102015, 102, '澳大利亚', '+61', '澳大利亚', 15, 1, NOW(), 1, NOW()),
(102016, 102, '印度尼西亚', '+62', '印度尼西亚', 16, 1, NOW(), 1, NOW()),
(102017, 102, '菲律宾', '+63', '菲律宾', 17, 1, NOW(), 1, NOW()),
(102018, 102, '新西兰', '+64', '新西兰', 18, 1, NOW(), 1, NOW()),
(102019, 102, '新加坡', '+65', '新加坡', 19, 1, NOW(), 1, NOW()),
(102020, 102, '泰国', '+66', '泰国', 20, 1, NOW(), 1, NOW()),
(102021, 102, '日本', '+81', '日本', 21, 1, NOW(), 1, NOW()),
(102022, 102, '韩国', '+82', '韩国', 22, 1, NOW(), 1, NOW()),
(102023, 102, '越南', '+84', '越南', 23, 1, NOW(), 1, NOW()),
(102024, 102, '印度', '+91', '印度', 24, 1, NOW(), 1, NOW()),
(102025, 102, '巴基斯坦', '+92', '巴基斯坦', 25, 1, NOW(), 1, NOW()),
(102026, 102, '尼日利亚', '+234', '尼日利亚', 26, 1, NOW(), 1, NOW()),
(102027, 102, '孟加拉国', '+880', '孟加拉国', 27, 1, NOW(), 1, NOW()),
(102028, 102, '沙特阿拉伯', '+966', '沙特阿拉伯', 28, 1, NOW(), 1, NOW()),
(102029, 102, '阿联酋', '+971', '阿联酋', 29, 1, NOW(), 1, NOW()),
(102030, 102, '巴西', '+55', '巴西', 30, 1, NOW(), 1, NOW()),
(102031, 102, '墨西哥', '+52', '墨西哥', 31, 1, NOW(), 1, NOW()),
(102032, 102, '智利', '+56', '智利', 32, 1, NOW(), 1, NOW()),
(102033, 102, '阿根廷', '+54', '阿根廷', 33, 1, NOW(), 1, NOW()),
(102034, 102, '埃及', '+20', '埃及', 34, 1, NOW(), 1, NOW()),
(102035, 102, '南非', '+27', '南非', 35, 1, NOW(), 1, NOW()),
(102036, 102, '肯尼亚', '+254', '肯尼亚', 36, 1, NOW(), 1, NOW()),
(102037, 102, '坦桑尼亚', '+255', '坦桑尼亚', 37, 1, NOW(), 1, NOW()),
(102038, 102, '哈萨克斯坦', '+7', '哈萨克斯坦', 38, 1, NOW(), 1, NOW());
