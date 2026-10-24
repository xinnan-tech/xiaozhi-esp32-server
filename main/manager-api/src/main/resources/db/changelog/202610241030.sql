-- 天气插件不再内置和风天气凭据
--
-- 早期版本把一把和风天气的 API Key 和一个 API Host 写在模型提供方
-- SYSTEM_PLUGIN_WEATHER 的字段默认值里。智控台的角色配置表单拿这个默认值预填，
-- 用户不填就等于沿用仓库里那一份。那把 key 已经失效，仓库里也不该带着凭据分发，
-- 用的人也不知道它从哪来、该不该用。
--
-- 这里清两处：
-- 1. 字段默认值置空，同时把申请路径写进字段名，用户在界面上就能看到去哪儿申请
-- 2. 已有智能体的参数里还等于内置值的那些，值清空。用户自己填的 key 不动
--
-- 内置值从模型提供方那一行现读，不写死在脚本里，免得仓库里再留一份凭据

SET @weather_api_key = (
    SELECT jt.`def`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_key` VARCHAR(64) PATH '$.key',
             `def` VARCHAR(255) PATH '$.default'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND jt.`field_key` = 'api_key'
    LIMIT 1
);

SET @weather_api_host = (
    SELECT jt.`def`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_key` VARCHAR(64) PATH '$.key',
             `def` VARCHAR(255) PATH '$.default'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND jt.`field_key` = 'api_host'
    LIMIT 1
);

-- 字段在数组里的位置。数组下标从 0 起，JSON_TABLE 的序号从 1 起，两者差一
SET @weather_api_key_pos = (
    SELECT jt.`ord`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `ord` FOR ORDINALITY,
             `field_key` VARCHAR(64) PATH '$.key'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND jt.`field_key` = 'api_key'
    LIMIT 1
);

SET @weather_api_host_pos = (
    SELECT jt.`ord`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `ord` FOR ORDINALITY,
             `field_key` VARCHAR(64) PATH '$.key'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND jt.`field_key` = 'api_host'
    LIMIT 1
);

-- 智能体参数里还等于内置值的项，清空。分两次更新，两项各自独立判断：
-- 用户自己填了 key 但没改 host 的，host 也要清掉，不然新 key 配旧 host 一样调不通
UPDATE `ai_agent_plugin_mapping`
SET `param_info` = JSON_SET(`param_info`, '$.api_key', '')
WHERE `plugin_id` = 'SYSTEM_PLUGIN_WEATHER'
  AND @weather_api_key IS NOT NULL
  AND @weather_api_key <> ''
  AND JSON_UNQUOTE(JSON_EXTRACT(`param_info`, '$.api_key')) = @weather_api_key;

UPDATE `ai_agent_plugin_mapping`
SET `param_info` = JSON_SET(`param_info`, '$.api_host', '')
WHERE `plugin_id` = 'SYSTEM_PLUGIN_WEATHER'
  AND @weather_api_host IS NOT NULL
  AND @weather_api_host <> ''
  AND JSON_UNQUOTE(JSON_EXTRACT(`param_info`, '$.api_host')) = @weather_api_host;

-- 字段默认值置空，字段名里写清申请路径。默认值那一栏在界面上还带着提示，
-- 光把值清空没用，填表的人根本不知道该去哪儿拿
UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    CONCAT('$[', @weather_api_key_pos - 1, '].default'), '',
    CONCAT('$[', @weather_api_key_pos - 1, '].label'),
    '天气插件 API 密钥（自己到和风天气控制台申请，步骤见 docs/weather-integration.md 的「API Key 申请指南」）',
    CONCAT('$[', @weather_api_host_pos - 1, '].default'), '',
    CONCAT('$[', @weather_api_host_pos - 1, '].label'),
    '开发者 API Host（和风天气控制台「设置」里查看，步骤见 docs/weather-integration.md 的「API Key 申请指南」）'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEATHER'
  AND @weather_api_key_pos IS NOT NULL
  AND @weather_api_host_pos IS NOT NULL;
