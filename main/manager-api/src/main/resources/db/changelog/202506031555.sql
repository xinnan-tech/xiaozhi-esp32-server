-- 增加火山大模型网关ASR供应器
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_ASR_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_VOLC_GW', 'ASR', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW());
-- 增加火山大模型网关TTS供应器
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_TTS_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_VOLC_GW', 'TTS', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW());
-- 增加火山大模型网关LLM供应器
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_LLM_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_LLM_VOLC_GW', 'LLM', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW());
-- 增加火山大模型网关VLM供应器
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_VLLM_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_VLLM_VOLC_GW', 'VLLM', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"}]', 1, 1, NOW(), 1, NOW());


-- 增加火山大模型网关ASR模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'ASR_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('ASR_VolceAIGateway', 'ASR', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"bigmodel\", \"host\": \"ai-gateway.vei.volces.com\", \"output_dir\": \"tmp/\"}', NULL, NULL, 16, 1, NOW(), 1, NOW());
-- 增加火山大模型网关TTS模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'TTS_VolcesAiGatewayTTS';
DELETE FROM `ai_model_config` WHERE `id` = 'TTS_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('TTS_VolceAIGateway', 'TTS', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"doubao-tts\", \"host\": \"ai-gateway.vei.volces.com\",\"voice\": \"zh_male_shaonianzixin_moon_bigtts\", \"speed\": 1, \"output_dir\": \"tmp/\"}', NULL, NULL, 16, 1, NOW(), 1, NOW());
-- 增加火山大模型网关LLM模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'LLM_VolcesAiGatewayLLM';
DELETE FROM `ai_model_config` WHERE `id` = 'LLM_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('LLM_VolceAIGateway', 'LLM', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"doubao-pro-32k-functioncall\", \"host\": \"ai-gateway.vei.volces.com\"}', NULL, NULL, 16, 1, NOW(), 1, NOW());
-- 增加火山大模型网关VLLM模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'VLLM_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('VLLM_VolceAIGateway', 'VLLM', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"doubao-1.5-vision-pro-32k\", \"host\": \"ai-gateway.vei.volces.com\"}', NULL, NULL, 16, 1, NOW(), 1, NOW());


-- 火山大模型网关ASR模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关ASR配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token）
3. 搜索并勾选 Doubao-语音识别，网关支持一个api_key访问ASR,LLM,TTS,VLLM模型，满足智能体使用，推荐同时开通“Doubao-语音识别”、“Doubao-语音合成”、“Doubao-pro-32k-functioncall”、“Doubao-1.5-vision-pro”全量模型
4. 填入配置文件中' WHERE `id` = 'ASR_VolceAIGateway';
-- 火山大模型网关TTS模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关TTS配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token）
3. 搜索并勾选 Doubao-语音合成，网关支持一个api_key访问ASR,LLM,TTS,VLLM模型，满足智能体使用，推荐同时开通“Doubao-语音识别”、“Doubao-语音合成”、“Doubao-pro-32k-functioncall”、“Doubao-1.5-vision-pro”全量模型
4. 填入配置文件中' WHERE `id` = 'TTS_VolceAIGateway';
-- 火山大模型网关LLM模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关LLM配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token）
3. 搜索并勾选 Doubao-pro-32k-functioncall，网关支持一个api_key访问ASR,LLM,TTS,VLLM模型，满足智能体使用，推荐同时开通“Doubao-语音识别”、“Doubao-语音合成”、“Doubao-pro-32k-functioncall”、“Doubao-1.5-vision-pro”全量模型
4. 填入配置文件中' WHERE `id` = 'LLM_VolceAIGateway';
-- 火山大模型网关VLLM模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关VLM配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token）
3. 搜索并勾选 Doubao-1.5-vision-pro，网关支持一个api_key访问ASR,LLM,TTS,VLLM模型，满足智能体使用，推荐同时开通“Doubao-语音识别”、“Doubao-语音合成”、“Doubao-pro-32k-functioncall”、“Doubao-1.5-vision-pro”全量模型
4. 填入配置文件中' WHERE `id` = 'VLLM_VolceAIGateway';


-- 添加火山引擎边缘大模型网关语音合成音色
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_VolceAIGateway';
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0001', 'TTS_VolceAIGateway', '灿灿/Shiny', 'zh_female_cancan_mars_bigtts', '中文、美式英语', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0002', 'TTS_VolceAIGateway', '清新女声', 'zh_female_qingxinnvsheng_mars_bigtts', '中文', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0003', 'TTS_VolceAIGateway', '爽快思思/Skye', 'zh_female_shuangkuaisisi_moon_bigtts', '中文、美式英语', NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0004', 'TTS_VolceAIGateway', '温暖阿虎/Alvin', 'zh_male_wennuanahu_moon_bigtts', '中文、美式英语', NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0005', 'TTS_VolceAIGateway', '少年梓辛/Brayan', 'zh_male_shaonianzixin_moon_bigtts', '中文、美式英语', NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0006', 'TTS_VolceAIGateway', '知性女声', 'zh_female_zhixingnvsheng_mars_bigtts', '中文', NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0007', 'TTS_VolceAIGateway', '清爽男大', 'zh_male_qingshuangnanda_mars_bigtts', '中文', NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0008', 'TTS_VolceAIGateway', '邻家女孩', 'zh_female_linjianvhai_moon_bigtts', '中文', NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0009', 'TTS_VolceAIGateway', '渊博小叔', 'zh_male_yuanboxiaoshu_moon_bigtts', '中文', NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0010', 'TTS_VolceAIGateway', '阳光青年', 'zh_male_yangguangqingnian_moon_bigtts', '中文', NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0011', 'TTS_VolceAIGateway', '甜美小源', 'zh_female_tianmeixiaoyuan_moon_bigtts', '中文', NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0012', 'TTS_VolceAIGateway', '清澈梓梓', 'zh_female_qingchezizi_moon_bigtts', '中文', NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0013', 'TTS_VolceAIGateway', '解说小明', 'zh_male_jieshuoxiaoming_moon_bigtts', '中文', NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0014', 'TTS_VolceAIGateway', '开朗姐姐', 'zh_female_kailangjiejie_moon_bigtts', '中文', NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0015', 'TTS_VolceAIGateway', '邻家男孩', 'zh_male_linjiananhai_moon_bigtts', '中文', NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0016', 'TTS_VolceAIGateway', '甜美悦悦', 'zh_female_tianmeiyueyue_moon_bigtts', '中文', NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0017', 'TTS_VolceAIGateway', '心灵鸡汤', 'zh_female_xinlingjitang_moon_bigtts', '中文', NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0018', 'TTS_VolceAIGateway', '知性温婉', 'ICL_zh_female_zhixingwenwan_tob', '中文', NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0019', 'TTS_VolceAIGateway', '暖心体贴', 'ICL_zh_male_nuanxintitie_tob', '中文', NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0020', 'TTS_VolceAIGateway', '温柔文雅', 'ICL_zh_female_wenrouwenya_tob', '中文', NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0021', 'TTS_VolceAIGateway', '开朗轻快', 'ICL_zh_male_kailangqingkuai_tob', '中文', NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0022', 'TTS_VolceAIGateway', '活泼爽朗', 'ICL_zh_male_huoposhuanglang_tob', '中文', NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0023', 'TTS_VolceAIGateway', '率真小伙', 'ICL_zh_male_shuaizhenxiaohuo_tob', '中文', NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0024', 'TTS_VolceAIGateway', '温柔小哥', 'zh_male_wenrouxiaoge_mars_bigtts', '中文', NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0025', 'TTS_VolceAIGateway', 'Smith', 'en_male_smith_mars_bigtts', '英式英语', NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0026', 'TTS_VolceAIGateway', 'Anna', 'en_female_anna_mars_bigtts', '英式英语', NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0027', 'TTS_VolceAIGateway', 'Adam', 'en_male_adam_mars_bigtts', '美式英语', NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0028', 'TTS_VolceAIGateway', 'Sarah', 'en_female_sarah_mars_bigtts', '澳洲英语', NULL, NULL, 28, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0029', 'TTS_VolceAIGateway', 'Dryw', 'en_male_dryw_mars_bigtts', '澳洲英语', NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0030', 'TTS_VolceAIGateway', 'かずね（和音）', 'multi_male_jingqiangkanye_moon_bigtts', '日语、西语', NULL, NULL, 30, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0031', 'TTS_VolceAIGateway', 'はるこ（晴子）', 'multi_female_shuangkuaisisi_moon_bigtts', '日语、西语', NULL, NULL, 31, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0032', 'TTS_VolceAIGateway', 'ひろし（広志）', 'multi_male_wanqudashu_moon_bigtts', '日语、西语', NULL, NULL, 32, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0033', 'TTS_VolceAIGateway', 'あけみ（朱美）', 'multi_female_gaolengyujie_moon_bigtts', '日语', NULL, NULL, 33, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0034', 'TTS_VolceAIGateway', 'Amanda', 'en_female_amanda_mars_bigtts', '美式英语', NULL, NULL, 34, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0035', 'TTS_VolceAIGateway', 'Jackson', 'en_male_jackson_mars_bigtts', '美式英语', NULL, NULL, 35, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0036', 'TTS_VolceAIGateway', '京腔侃爷/Harmony', 'zh_male_jingqiangkanye_moon_bigtts', '中文-北京口音、英文', NULL, NULL, 36, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0037', 'TTS_VolceAIGateway', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文-台湾口音', NULL, NULL, 37, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0038', 'TTS_VolceAIGateway', '湾区大叔', 'zh_female_wanqudashu_moon_bigtts', '中文-广东口音', NULL, NULL, 38, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0039', 'TTS_VolceAIGateway', '呆萌川妹', 'zh_female_daimengchuanmei_moon_bigtts', '中文-四川口音', NULL, NULL, 39, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0040', 'TTS_VolceAIGateway', '广州德哥', 'zh_male_guozhoudege_moon_bigtts', '中文-广东口音', NULL, NULL, 40, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0041', 'TTS_VolceAIGateway', '北京小爷', 'zh_male_beijingxiaoye_moon_bigtts', '中文-北京口音', NULL, NULL, 41, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0042', 'TTS_VolceAIGateway', '浩宇小哥', 'zh_male_haoyuxiaoge_moon_bigtts', '中文-青岛口音', NULL, NULL, 42, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0043', 'TTS_VolceAIGateway', '广西远舟', 'zh_male_guangxiyuanzhou_moon_bigtts', '中文-广西口音', NULL, NULL, 43, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0044', 'TTS_VolceAIGateway', '妹坨洁儿', 'zh_female_meituojieer_moon_bigtts', '中文-长沙口音', NULL, NULL, 44, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolceAIGateway_0045', 'TTS_VolceAIGateway', '豫州子轩', 'zh_male_yuzhouzixuan_moon_bigtts', '中文-河南口音', NULL, NULL, 45, NULL, NULL, NULL, NULL);