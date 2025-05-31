-- ===============================
-- 一、在ai_model_provider中插入plugin 记录
-- ===============================
START TRANSACTION;

-- 1. 天气查询
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_WEATHER',
        'Plugin',
        'get_weather',
        '天气查询',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', '天气插件 API 密钥',
                        'default', (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_key')
                ),
                JSON_OBJECT(
                        'key', 'default_location',
                        'type', 'string',
                        'label', '默认查询城市',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.default_location')
                ),
                JSON_OBJECT(
                        'key', 'api_host',
                        'type', 'string',
                        'label', '开发者 API Host',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_host')
                )
        ),
        10, 0, NOW(), 0, NOW());

-- 2. 新闻订阅
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_NEWS',
        'Plugin',
        'get_news_from_newsnow',
        '新闻订阅',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'default_rss_url',
                        'type', 'string',
                        'label', '默认 RSS 源',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_news.default_rss_url')
                ),
                JSON_OBJECT(
                        'key', 'category_urls',
                        'type', 'json',
                        'label', '分类 RSS 地址映射',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_news.category_urls')
                )
        ),
        20, 0, NOW(), 0, NOW());

-- 3. HomeAssistant 状态查询
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_GET_STATE',
        'Plugin',
        'hass_get_state',
        'HomeAssistant 状态查询',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'base_url',
                        'type', 'string',
                        'label', 'HA 服务器地址',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.base_url')
                ),
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', 'HA API 访问令牌',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.api_key')
                ),
                JSON_OBJECT(
                        'key', 'devices',
                        'type', 'array',
                        'label', '设备列表（名称,实体ID;…）',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.devices')
                )
        ),
        30, 0, NOW(), 0, NOW());

-- 4. HomeAssistant 状态写入
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_SET_STATE',
        'Plugin',
        'hass_set_state',
        'HomeAssistant 状态写入',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'base_url',
                        'type', 'string',
                        'label', 'HA 服务器地址',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.base_url')
                ),
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', 'HA API 访问令牌',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.api_key')
                ),
                JSON_OBJECT(
                        'key', 'devices',
                        'type', 'array',
                        'label', '设备列表（名称,实体ID;…）',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.devices')
                )
        ),
        40, 0, NOW(), 0, NOW());

-- 5. 本地播放
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_MUSIC',
        'Plugin',
        'play_music',
        '本地播放',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'music_dir',
                        'type', 'string',
                        'label', '音乐文件根目录',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.play_music.music_dir')
                ),
                JSON_OBJECT(
                        'key', 'music_ext',
                        'type', 'array',
                        'label', '支持的文件后缀',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.play_music.music_ext')
                ),
                JSON_OBJECT(
                        'key', 'refresh_time',
                        'type', 'number',
                        'label', '列表刷新间隔（秒）',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.play_music.refresh_time')
                )
        ),
        50, 0, NOW(), 0, NOW());


-- ===============================
-- 二、删除sys_params中旧的plugins.*参数
-- ===============================
DELETE
FROM sys_params
WHERE param_code LIKE 'plugins.%';


-- ===============================
-- 三、添加智能体插件id字段
-- ===============================
CREATE TABLE IF NOT EXISTS ai_agent_plugin_mapping
(
    id         BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    agent_id   VARCHAR(32) NOT NULL COMMENT '智能体ID',
    plugin_id  VARCHAR(32) NOT NULL COMMENT '插件ID',
    param_info JSON        NOT NULL COMMENT '参数信息',
    UNIQUE KEY uk_agent_provider (agent_id, plugin_id)
) COMMENT 'Agent与插件的唯一映射表';


COMMIT;

