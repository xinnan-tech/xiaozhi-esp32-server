-- 本地短期记忆配置可以设置独立的LLM
update `ai_model_provider` set fields =  '[{"key":"llm","label":"LLM模型","type":"string"}]' where  id = 'SYSTEM_Memory_mem_local_short';
update `ai_model_config` set config_json =  '{\"type\": \"mem_local_short\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Memory_mem_local_short';

-- 增加火山双流式TTS供应器和模型配置
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_HSDSTTS', 'TTS', 'huoshan_double_stream', '火山双流式语音合成', '[{"key":"ws_url","label":"WebSocket地址","type":"string"},{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"resource_id","label":"资源ID","type":"string"},{"key":"speaker","label":"默认音色","type":"string"}]', 13, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'TTS_HuoshanDoubleStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_HuoshanDoubleStreamTTS', 'TTS', 'HuoshanDoubleStreamTTS', '火山双流式语音合成', 0, 1, '{\"type\": \"huoshan_double_stream\", \"ws_url\": \"wss://openspeech.bytedance.com/api/v3/tts/bidirection\", \"appid\": \"你的火山引擎语音合成服务appid\", \"access_token\": \"你的火山引擎语音合成服务access_token\", \"resource_id\": \"volc.service_type.10029\", \"speaker\": \"zh_female_wanwanxiaohe_moon_bigtts\"}', NULL, NULL, 16, NULL, NULL, NULL, NULL);

-- 火山双流式TT模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 填入配置文件中' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';


-- 添加火山双流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_HuoshanDoubleStreamTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0001', 'TTS_HuoshanDoubleStreamTTS', '爽快思思/Skye', 'zh_female_shuangkuaisisi_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Skye.mp3', NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0002', 'TTS_HuoshanDoubleStreamTTS', '温暖阿虎/Alvin', 'zh_male_wennuanahu_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Alvin.mp3', NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0003', 'TTS_HuoshanDoubleStreamTTS', '少年梓辛/Brayan', 'zh_male_shaonianzixin_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Brayan.mp3', NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0004', 'TTS_HuoshanDoubleStreamTTS', '邻家女孩', 'zh_female_linjianvhai_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%82%BB%E5%AE%B6%E5%A5%B3%E5%AD%A9.mp3', NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0005', 'TTS_HuoshanDoubleStreamTTS', '渊博小叔', 'zh_male_yuanboxiaoshu_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B8%8A%E5%8D%9A%E5%B0%8F%E5%8F%94.mp3', NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0006', 'TTS_HuoshanDoubleStreamTTS', '阳光青年', 'zh_male_yangguangqingnian_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%98%B3%E5%85%89%E9%9D%92%E5%B9%B4.mp3', NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0007', 'TTS_HuoshanDoubleStreamTTS', '京腔侃爷/Harmony', 'zh_male_jingqiangkanye_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Harmony.mp3', NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0008', 'TTS_HuoshanDoubleStreamTTS', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0009', 'TTS_HuoshanDoubleStreamTTS', '湾区大叔', 'zh_female_wanqudashu_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E5%8C%BA%E5%A4%A7%E5%8F%94.mp3', NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0010', 'TTS_HuoshanDoubleStreamTTS', '呆萌川妹', 'zh_female_daimengchuanmei_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%91%86%E8%90%8C%E5%B7%9D%E5%A6%B9.mp3', NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0011', 'TTS_HuoshanDoubleStreamTTS', '广州德哥', 'zh_male_guozhoudege_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E5%B7%9E%E5%BE%B7%E5%93%A5.mp3', NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0012', 'TTS_HuoshanDoubleStreamTTS', '北京小爷', 'zh_male_beijingxiaoye_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%8C%97%E4%BA%AC%E5%B0%8F%E7%88%B7.mp3', NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0013', 'TTS_HuoshanDoubleStreamTTS', '浩宇小哥', 'zh_male_haoyuxiaoge_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B5%A9%E5%AE%87%E5%B0%8F%E5%93%A5.mp3', NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0014', 'TTS_HuoshanDoubleStreamTTS', '广西远舟', 'zh_male_guangxiyuanzhou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E8%A5%BF%E8%BF%9C%E8%88%9F.mp3', NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0015', 'TTS_HuoshanDoubleStreamTTS', '妹坨洁儿', 'zh_female_meituojieer_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%A6%B9%E5%9D%A8%E6%B4%81%E5%84%BF.mp3', NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0016', 'TTS_HuoshanDoubleStreamTTS', '豫州子轩', 'zh_male_yuzhouzixuan_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E8%B1%AB%E5%B7%9E%E5%AD%90%E8%BD%A9.mp3', NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0017', 'TTS_HuoshanDoubleStreamTTS', '高冷御姐', 'zh_female_gaolengyujie_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AB%98%E5%86%B7%E5%BE%A1%E5%A7%90.mp3', NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0018', 'TTS_HuoshanDoubleStreamTTS', '傲娇霸总', 'zh_male_aojiaobazong_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%82%B2%E5%A8%87%E9%9C%B8%E6%80%BB.mp3', NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0019', 'TTS_HuoshanDoubleStreamTTS', '魅力女友', 'zh_female_meilinvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AD%85%E5%8A%9B%E5%A5%B3%E5%8F%8B.mp3', NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0020', 'TTS_HuoshanDoubleStreamTTS', '深夜播客', 'zh_male_shenyeboke_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B7%B1%E5%A4%9C%E6%92%AD%E5%AE%A2.mp3', NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0021', 'TTS_HuoshanDoubleStreamTTS', '柔美女友', 'zh_female_sajiaonvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9F%94%E7%BE%8E%E5%A5%B3%E5%8F%8B.mp3', NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0022', 'TTS_HuoshanDoubleStreamTTS', '撒娇学妹', 'zh_female_yuanqinvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%92%92%E5%A8%87%E5%AD%A6%E5%A6%B9.mp3', NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0023', 'TTS_HuoshanDoubleStreamTTS', 'かずね（和音）', 'multi_male_jingqiangkanye_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Javier.wav', NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0024', 'TTS_HuoshanDoubleStreamTTS', 'はるこ（晴子）', 'multi_female_shuangkuaisisi_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Esmeralda.mp3', NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0025', 'TTS_HuoshanDoubleStreamTTS', 'あけみ（朱美）', 'multi_female_gaolengyujie_moon_bigtts', '日语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9C%B1%E7%BE%8E.mp3', NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0026', 'TTS_HuoshanDoubleStreamTTS', 'ひろし（広志）', 'multi_male_wanqudashu_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Roberto.wav', NULL, 26, NULL, NULL, NULL, NULL);
