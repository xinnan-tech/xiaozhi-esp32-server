-- 添加百度ASR模型配置
delete from `ai_model_config` where `id` = 'ASR_BaiduASR';
INSERT INTO `ai_model_config` VALUES ('ASR_BaiduASR', 'ASR', 'BaiduASR', '百度语音识别', 0, 1, '{\"type\": \"baidu\", \"app_id\": \"\", \"api_key\": \"\", \"secret_key\": \"\", \"dev_pid\": 1537, \"output_dir\": \"tmp/\"}', NULL, NULL, 7, NULL, NULL, NULL, NULL);


-- 添加百度ASR供应器
delete from `ai_model_provider` where `id` = 'SYSTEM_ASR_BaiduASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_BaiduASR', 'ASR', 'baidu', '百度语音识别', '[{"key":"app_id","label":"应用AppID","type":"string"},{"key":"api_key","label":"API Key","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"dev_pid","label":"语言参数","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 7, 1, NOW(), 1, NOW());


-- 更新百度ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.bce.baidu.com/ai-engine/old/#/ai/speech/app/list',
`remark` = '百度ASR配置说明：
1. 访问 https://console.bce.baidu.com/ai-engine/old/#/ai/speech/app/list
2. 创建新应用
3. 获取AppID、API Key和Secret Key
4. 填入配置文件中
查看资源额度：https://console.bce.baidu.com/ai-engine/old/#/ai/speech/overview/resource/list
语言参数说明：https://ai.baidu.com/ai-doc/SPEECH/0lbxfnc9b
' WHERE `id` = 'ASR_BaiduASR';

-- 更新豆包供应器字段
update `ai_model_provider` set `fields` = 
'[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]'
where `id` = 'SYSTEM_ASR_DoubaoASR';

-- 更新豆包ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 需要在火山引擎控制台创建应用并获取appid和access_token
2. 支持中文语音识别
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoASR';