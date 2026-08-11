UPDATE sys_params
SET param_value = ''
WHERE param_code = 'plugins.get_weather.api_key'
  AND param_value = 'a861d0d5e7bf4ee1a83d9a9e4f96d4da';

UPDATE ai_model_provider
SET fields = JSON_ARRAY(
    JSON_OBJECT(
        'key', 'auth_type',
        'type', 'select',
        'label', '认证方式',
        'default', 'api_key',
        'options', JSON_ARRAY(
            JSON_OBJECT('label', 'API Key', 'value', 'api_key'),
            JSON_OBJECT('label', 'JWT', 'value', 'jwt')
        )
    ),
    JSON_OBJECT(
        'key', 'api_key',
        'type', 'password',
        'label', '天气插件 API Key',
        'default', (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_key'),
        'visible_when', JSON_OBJECT('auth_type', 'api_key')
    ),
    JSON_OBJECT(
        'key', 'project_id',
        'type', 'string',
        'label', 'QWeather Project ID',
        'default', '',
        'visible_when', JSON_OBJECT('auth_type', 'jwt')
    ),
    JSON_OBJECT(
        'key', 'credential_id',
        'type', 'string',
        'label', 'QWeather Credential ID',
        'default', '',
        'visible_when', JSON_OBJECT('auth_type', 'jwt')
    ),
    JSON_OBJECT(
        'key', 'private_key',
        'type', 'file',
        'label', 'Ed25519 PKCS#8 私钥',
        'default', '',
        'accept', '.pem',
        'visible_when', JSON_OBJECT('auth_type', 'jwt')
    ),
    JSON_OBJECT(
        'key', 'default_location',
        'type', 'string',
        'label', '默认查询城市',
        'default', (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.default_location')
    ),
    JSON_OBJECT(
        'key', 'api_host',
        'type', 'string',
        'label', '开发者 API Host',
        'default', (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_host')
    )
)
WHERE id = 'SYSTEM_PLUGIN_WEATHER';
