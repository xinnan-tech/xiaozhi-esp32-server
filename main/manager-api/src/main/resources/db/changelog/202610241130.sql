-- 兜底：早期版本把天气插件的凭据放在系统参数里，那两条记录后来被 202505292203.sql
-- 删掉了，新装的库里本来就没有这两行。这里再置一次空，防止有环境绕过了那步删除。
-- 正常情况下影响零行
--
-- 这条变更记录在 db.changelog-master.yaml 里标了 runOnChange：脚本内容在这个
-- PR 里改过，跑过旧版的库启动时直接重跑新版，不会报校验不一致。那不是手滑
--
-- 只清从没被人改过的行：系统参数界面里这两行也能改，管理员填进去的凭据不能被抹掉。
-- 种子数据插进来时没写 updater 和 update_date，这两列是空的；界面上保存过一次之后
-- 就会写上操作人和时间
UPDATE `sys_params`
SET `param_value` = ''
WHERE `param_code` IN ('plugins.get_weather.api_key', 'plugins.get_weather.api_host')
  AND `updater` IS NULL
  AND `update_date` IS NULL;
