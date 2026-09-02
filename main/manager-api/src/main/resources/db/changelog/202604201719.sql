-- 新增豆包语音合成模型2.0供应器（使用seed-tts-2.0资源ID）
-- 与火山双流式TTS配置相同，但resource_id固定为seed-tts-2.0

-- 插入豆包语音合成模型2.0供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS_V2';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_HSDSTTS_V2', 'TTS', 'huoshan_double_stream', '豆包语音合成模型2.0', '[
  {"key": "ws_url", "type": "string", "label": "WebSocket地址"},
  {"key": "appid", "type": "string", "label": "应用ID"},
  {"key": "access_token", "type": "string", "label": "访问令牌"},
  {"key": "resource_id", "type": "string", "label": "资源ID"},
  {"key": "speaker", "type": "string", "label": "默认音色"},
  {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true},
  {"key": "audio_params", "type": "dict", "label": "音频输出配置"},
  {"key": "additions", "type": "dict", "label": "高级文本处理配置"},
  {"key": "mix_speaker", "type": "dict", "label": "混音控制配置"}
]', 14, 1, NOW(), 1, NOW());

-- 插入豆包语音合成模型2.0配置
delete from `ai_model_config` where id = 'TTS_HSDSTTS_V2';
INSERT INTO `ai_model_config` VALUES ('TTS_HSDSTTS_V2', 'TTS', 'HuoshanDoubleStreamTTSV2', '豆包语音合成模型2.0', 0, 1, '{
  "type": "huoshan_double_stream",
  "ws_url": "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
  "appid": "",
  "access_token": "",
  "resource_id": "seed-tts-2.0",
  "speaker": "zh_female_xiaohe_uranus_bigtts",
  "enable_ws_reuse": true,
  "audio_params": {
    "speech_rate": 0,
    "loudness_rate": 0
  },
  "additions": {
    "aigc_metadata": {},
    "cache_config": {},
    "post_process": {
      "pitch": 0
    }
  },
  "mix_speaker": {}
}', NULL, NULL, 17, NULL, NULL, NULL, NULL);

-- 豆包语音合成模型2.0配置说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.volcengine.com/docs/6561/1329505',
`remark` = '豆包语音合成模型2.0配置说明（基于火山引擎seed-tts-2.0）：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10035 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
4. 资源ID固定为：seed-tts-2.0（豆包语音合成模型2.0）
5. 链接复用：开启WebSocket连接复用，默认true减少链接损耗（注意：复用后设备处于聆听状态时空闲链接会占并发数）

详细参数文档：https://www.volcengine.com/docs/6561/1329505
【audio_params】音频输出配置 - 用户可自定义添加火山引擎支持的任何音频参数
  - speech_rate: 语速(-50~100)，默认0
  - loudness_rate: 音量(-50~100)，默认0
  示例：{"speech_rate": 10, "loudness_rate": 5}

【additions】高级文本处理配置 - 用户可自定义添加火山引擎支持的任何高级参数
  - post_process.pitch: 音高(-12~12)，默认0
  - aigc_metadata: AIGC元数据配置
  - cache_config: 缓存配置
  示例：{"post_process": {"pitch": 2}, "aigc_metadata": {}, "cache_config": {}}

注意：
- 豆包语音合成模型2.0使用seed-tts-2.0资源ID，与火山双流式TTS（volc.service_type.10029）不同
- 相关音色列表：https://www.volcengine.com/docs/6561/1257544
- 用户可根据火山引擎API文档自行添加更多参数
' WHERE `id` = 'TTS_HSDSTTS_V2';

-- 添加豆包语音合成模型2.0音色（与火山双流式TTS音色相同）
delete from `ai_tts_voice` where tts_model_id = 'TTS_HSDSTTS_V2';
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0001', 'TTS_HSDSTTS_V2', 'Vivi', 'zh_female_vv_uranus_bigtts', '普通话、日语、印尼语、墨西哥西班牙语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_vv_uranus_bigtts.wav', NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0002', 'TTS_HSDSTTS_V2', '小何', 'zh_female_xiaohe_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_xiaohe_uranus_bigtts.mp3', NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0003', 'TTS_HSDSTTS_V2', '云舟', 'zh_male_m191_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_m191_uranus_bigtts.mp3', NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0004', 'TTS_HSDSTTS_V2', '小天', 'zh_male_taocheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_taocheng_uranus_bigtts.mp3', NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0005', 'TTS_HSDSTTS_V2', '刘飞', 'zh_male_liufei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_liufei_uranus_bigtts.mp3', NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0006', 'TTS_HSDSTTS_V2', '魅力苏菲', 'zh_female_sophie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sophie_uranus_bigtts.mp3', NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0007', 'TTS_HSDSTTS_V2', '清新女声', 'zh_female_qingxinnvsheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_qingxinnvsheng_uranus_bigtts.mp3', NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0008', 'TTS_HSDSTTS_V2', '知性灿灿', 'zh_female_cancan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_cancan_uranus_bigtts.mp3', NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0009', 'TTS_HSDSTTS_V2', '撒娇学妹', 'zh_female_sajiaoxuemei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_sajiaoxuemei_uranus_bigtts.mp3', NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0010', 'TTS_HSDSTTS_V2', '甜美小源', 'zh_female_tianmeixiaoyuan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeixiaoyuan_uranus_bigtts.mp3', NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0011', 'TTS_HSDSTTS_V2', '甜美桃子', 'zh_female_tianmeitaozi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeitaozi_uranus_bigtts.mp3', NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0012', 'TTS_HSDSTTS_V2', '爽快思思', 'zh_female_shuangkuaisisi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_shuangkuaisisi_uranus_bigtts.mp3', NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0013', 'TTS_HSDSTTS_V2', '佩奇猪', 'zh_female_peiqi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_peiqi_uranus_bigtts.mp3', NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0014', 'TTS_HSDSTTS_V2', '邻家女孩', 'zh_female_linjianvhai_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_linjianvhai_uranus_bigtts.mp3', NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0015', 'TTS_HSDSTTS_V2', '少年梓辛/Brayan', 'zh_male_shaonianzixin_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_shaonianzixin_uranus_bigtts.mp3', NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0016', 'TTS_HSDSTTS_V2', '猴哥', 'zh_male_sunwukong_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sunwukong_uranus_bigtts.mp3', NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0017', 'TTS_HSDSTTS_V2', '魅力女友', 'zh_female_meilinvyou_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_meilinvyou_uranus_bigtts.mp3', NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0018', 'TTS_HSDSTTS_V2', 'Tim', 'en_male_tim_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_male_tim_uranus_bigtts.mp3', NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0019', 'TTS_HSDSTTS_V2', 'Dacey', 'en_female_dacey_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_dacey_uranus_bigtts.mp3', NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0020', 'TTS_HSDSTTS_V2', 'Stokie', 'en_female_stokie_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_stokie_uranus_bigtts.mp3', NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0021', 'TTS_HSDSTTS_V2', '温暖阿虎/Alvin', 'zh_male_wennuanahu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_wennuanahu_uranus_bigtts.mp3', NULL, NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0022', 'TTS_HSDSTTS_V2', '奶气萌娃', 'zh_male_naiqimengwa_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_naiqimengwa_uranus_bigtts.mp3', NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0023', 'TTS_HSDSTTS_V2', '婆婆', 'zh_female_popo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_popo_uranus_bigtts.mp3', NULL, NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0024', 'TTS_HSDSTTS_V2', '开朗姐姐', 'zh_female_kailangjiejie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_kailangjiejie_uranus_bigtts.mp3', NULL, NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0025', 'TTS_HSDSTTS_V2', '轻盈朵朵', 'saturn_zh_female_qingyingduoduo_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_qingyingduoduo_cs_tob.mp3', NULL, NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0026', 'TTS_HSDSTTS_V2', '温婉珊珊', 'saturn_zh_female_wenwanshanshan_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_wenwanshanshan_cs_tob.mp3', NULL, NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0027', 'TTS_HSDSTTS_V2', '霸气青叔', 'zh_male_baqiqingshu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_baqiqingshu_uranus_bigtts.mp3', NULL, NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0028', 'TTS_HSDSTTS_V2', '悬疑解说', 'zh_male_xuanyijieshuo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_xuanyijieshuo_uranus_bigtts.mp3', NULL, NULL, NULL, 28, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0029', 'TTS_HSDSTTS_V2', '古风少御', 'zh_female_gufengshaoyu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_gufengshaoyu_uranus_bigtts.mp3', NULL, NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0030', 'TTS_HSDSTTS_V2', '唐僧', 'zh_male_tangseng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_tangseng_uranus_bigtts.mp3', NULL, NULL, NULL, 30, NULL, NULL, NULL, NULL);
