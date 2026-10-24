-- 兜底：早期版本把天气插件的凭据放在系统参数里，那两条记录后来被 202505292203.sql
-- 删掉了，新装的库里本来就没有这两行。这里再置一次空，防止有环境绕过了那步删除。
-- 正常情况下影响零行
UPDATE `sys_params`
SET `param_value` = ''
WHERE `param_code` IN ('plugins.get_weather.api_key', 'plugins.get_weather.api_host');
