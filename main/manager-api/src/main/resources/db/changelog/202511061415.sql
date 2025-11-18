-- 添加memU记忆配置
-- memU是一个开源的AI记忆框架，提供长期记忆管理服务

-- 添加memU Memory Provider
delete from `ai_model_provider` where id = 'SYSTEM_Memory_memu';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_Memory_memu', 'Memory', 'memu', 'memU记忆', '[{"key":"api_key","label":"API密钥","type":"password"},{"key":"base_url","label":"API地址","type":"string"},{"key":"user_name","label":"用户名称","type":"string"},{"key":"agent_name","label":"Agent名称","type":"string"}]', 4, 1, NOW(), 1, NOW());

-- 添加memU Memory Config
delete from `ai_model_config` where id = 'Memory_memu';
INSERT INTO `ai_model_config` VALUES (
    'Memory_memu',
    'Memory',
    'memu',
    'memU记忆',
    0,
    1,
    '{"type": "memu", "api_key": "mu_SJPB0t8dtY0IwL0B0RjpiVKbTEI4w8MD8YkYSVItNzxe-t3DlOtHIJnp53tJ-kr6BL06-uPN0U5WPGs4EpT5iuMZMsrfI1KYvVfg1w", "base_url": "https://api.memu.so", "user_name": "用户", "agent_name": "小智"}',
    'https://memu.pro/docs#memory',
    'memU是一个开源的AI记忆框架，提供自主管理、组织和演进AI记忆的高级代理记忆系统。支持自动分类、语义搜索和长期记忆管理。',
    4,
    NULL,
    NULL,
    NULL,
    NULL
);
