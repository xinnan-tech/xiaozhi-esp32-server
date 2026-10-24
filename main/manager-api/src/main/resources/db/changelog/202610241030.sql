-- 天气插件不再内置和风天气凭据
--
-- 这条变更记录在 db.changelog-master.yaml 里标了 runOnChange：脚本内容在这个
-- PR 里改过好几轮，跑过旧版的库启动时直接重跑新版，不会报校验不一致。
-- 那不是手滑，别删掉这个标记
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
-- 关键前提：模型提供方那一行的「默认值」管理员能在界面上改，不能直接拿它当
-- 「内置值」的基准——那样会把管理员自己填的凭据清掉。判断这一行有没有被人动过，
-- 看两列：种子数据插进来的时候 updater 是 0、update_date 跟 create_date 一样；
-- 界面上保存过一次之后，updater 变成操作人、update_date 变成改的时间。
-- 只有从没被改过的那一行，它里面的默认值才是仓库内置的那一份，才拿来当基准。
-- 被改过的一律不动——那是管理员自己的值，误清就是误删人家的凭据。
--
-- 有一处清不干净，说明白：管理员动过这一行之后，仓库内置的那把失效 key 就再也
-- 认不出来了（它被管理员的值覆盖了），早期建立、参数里还存着那把失效 key 的智能体
-- 只能由管理员自己在界面上改。默认配置那边同理，只能整行不动。
--
-- 内置值从模型提供方那一行现读，不写死在脚本里，免得仓库里再留一份凭据

-- 基准行有没有被人编辑过
SET @weather_provider_untouched = (
    SELECT COUNT(*)
    FROM `ai_model_provider`
    WHERE `id` = 'SYSTEM_PLUGIN_WEATHER'
      AND `updater` = 0
      AND `update_date` = `create_date`
);

-- 内置值。基准行被改过就没有内置值可比，取不到
SET @weather_api_key = (
    SELECT jt.`field_default`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_key` VARCHAR(64) PATH '$.key',
             `field_default` VARCHAR(255) PATH '$.default'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND @weather_provider_untouched > 0
      AND jt.`field_key` = 'api_key'
    LIMIT 1
);

SET @weather_api_host = (
    SELECT jt.`field_default`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_key` VARCHAR(64) PATH '$.key',
             `field_default` VARCHAR(255) PATH '$.default'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND @weather_provider_untouched > 0
      AND jt.`field_key` = 'api_host'
    LIMIT 1
);

-- 字段在数组里的位置。数组下标从 0 起，JSON_TABLE 的序号从 1 起，两者差一
SET @weather_api_key_pos = (
    SELECT jt.`field_ord`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_ord` FOR ORDINALITY,
             `field_key` VARCHAR(64) PATH '$.key'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND @weather_provider_untouched > 0
      AND jt.`field_key` = 'api_key'
    LIMIT 1
);

SET @weather_api_host_pos = (
    SELECT jt.`field_ord`
    FROM `ai_model_provider` p,
         JSON_TABLE(p.`fields`, '$[*]' COLUMNS (
             `field_ord` FOR ORDINALITY,
             `field_key` VARCHAR(64) PATH '$.key'
         )) jt
    WHERE p.`id` = 'SYSTEM_PLUGIN_WEATHER'
      AND @weather_provider_untouched > 0
      AND jt.`field_key` = 'api_host'
    LIMIT 1
);

-- 智能体参数里还等于内置值的项，清空。基准行被改过就取不到内置值，这时一律不动：
-- 管理员自己填的值不能碰，早于管理员编辑建立的智能体里存的旧内置值也认不出来了
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
-- 两项各自一条更新，各守卫各的字段位置：管理员把其中一项的字段删了，
-- 另一项的默认值照样要清掉，不能因为少一个位置就整条都跳过
UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    CONCAT('$[', @weather_api_key_pos - 1, '].default'), '',
    CONCAT('$[', @weather_api_key_pos - 1, '].label'),
    '天气插件 API 密钥（到和风天气控制台 https://console.qweather.com/project?lang=zh 申请，创建应用时勾选 GeoAPI 城市查询、实时天气、7 天天气预报三项权限；仓库里的 docs/weather-integration.md 有申请步骤）'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEATHER'
  AND @weather_provider_untouched > 0
  AND @weather_api_key_pos IS NOT NULL;

UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    CONCAT('$[', @weather_api_host_pos - 1, '].default'), '',
    CONCAT('$[', @weather_api_host_pos - 1, '].label'),
    '开发者 API Host（和风天气控制台「设置」https://console.qweather.com/setting?lang=zh 里查看，跟 API 密钥配套使用；仓库里的 docs/weather-integration.md 有申请步骤）'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEATHER'
  AND @weather_provider_untouched > 0
  AND @weather_api_host_pos IS NOT NULL;
