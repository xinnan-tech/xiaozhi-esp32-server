-- 联网搜索插件新增Serply搜索源

UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    '$[0].label',
    '搜索源：metaso / tavily / serply'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEB_SEARCH';
