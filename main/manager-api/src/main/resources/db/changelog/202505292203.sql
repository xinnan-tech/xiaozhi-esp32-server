-- ===============================
-- 一、在ai_model_provider中插入plugin 记录
-- ===============================
START TRANSACTION;


-- intent_llm和function_call不设置函数列表
update `ai_model_provider` set fields =  '[{"key":"llm","label":"LLM模型","type":"string"}]' where  id = 'SYSTEM_Intent_intent_llm';
update `ai_model_provider` set fields =  '[]' where  id = 'SYSTEM_Intent_function_call';
update `ai_model_config` set config_json =  '{\"type\": \"intent_llm\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Intent_intent_llm';
UPDATE `ai_model_config` SET config_json = '{\"type\": \"function_call\"}' WHERE id = 'Intent_function_call';


delete from ai_model_provider where model_type = 'Plugin';
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

-- 6. 本地播放音乐
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_MUSIC',
        'Plugin',
        'play_music',
        '服务器音乐播放',
        JSON_ARRAY(),
        20, 0, NOW(), 0, NOW());

-- 2. 新闻订阅
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_NEWS_CHINANEWS',
        'Plugin',
        'get_news_from_chinanews',
        '中新网新闻',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'default_rss_url',
                        'type', 'string',
                        'label', '默认 RSS 源',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_news.default_rss_url')
                ),
                JSON_OBJECT(
                        'key', 'society_rss_url',
                        'type', 'string',
                        'label', '社会新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/society.xml'
                ),
                JSON_OBJECT(
                        'key', 'world_rss_url',
                        'type', 'string',
                        'label', '国际新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/world.xml'
                ),
                JSON_OBJECT(
                        'key', 'finance_rss_url',
                        'type', 'string',
                        'label', '财经新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/finance.xml'
                )
        ),
        30, 0, NOW(), 0, NOW());

-- 3. 新闻订阅
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_NEWS_NEWSNOW',
        'Plugin',
        'get_news_from_newsnow',
        'newsnow新闻聚合',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'url',
                        'type', 'string',
                        'label', '接口地址',
                        'default',
                        'https://newsnow.busiyi.world/api/s?id='
                )
        ),
        40, 0, NOW(), 0, NOW());


-- 4. HomeAssistant 状态查询
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_GET_STATE',
        'Plugin',
        'hass_get_state',
        'HomeAssistant设备状态查询',
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
        50, 0, NOW(), 0, NOW());

-- 5. HomeAssistant 状态写入
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_SET_STATE',
        'Plugin',
        'hass_set_state',
        'HomeAssistant设备状态修改',
        JSON_ARRAY(),
        60, 0, NOW(), 0, NOW());

-- 5. HomeAssistant 音乐播放
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_PLAY_MUSIC',
        'Plugin',
        'hass_play_music',
        'HomeAssistant音乐播放',
        JSON_ARRAY(),
        70, 0, NOW(), 0, NOW());


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

