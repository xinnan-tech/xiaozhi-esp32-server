-- 修复豆包语音合成模型2.0 provider_code 重复问题，添加 ASR 2.0 支持

-- ==================== 豆包语音合成模型2.0 ====================
-- 删除 TTS 2.0 供应器（不再需要单独的供应器）
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS_V2';

-- ==================== 豆包语音识别(流式) ====================
-- 修正原有豆包语音识别(流式)供应器，移除cluster字段，添加resource_id字段
UPDATE `ai_model_provider` SET `fields` = '[{"key":"appid","type":"string","label":"应用ID"},{"key":"access_token","type":"string","label":"访问令牌"},{"key":"boosting_table_name","type":"string","label":"热词文件名称"},{"key":"correct_table_name","type":"string","label":"替换词文件名称"},{"key":"output_dir","type":"string","label":"输出目录"},{"key":"end_window_size","type":"number","label":"静音判定时长(ms)"},{"key":"enable_multilingual","type":"boolean","label":"是否开启多语种识别模式"},{"key":"language","type":"string","label":"指定语言编码"},{"key":"resource_id","type":"string","label":"资源ID"}]' WHERE `id` = 'SYSTEM_ASR_DoubaoStreamASR';

-- 修正原有豆包语音识别(流式)配置，移除cluster字段，添加resource_id默认值
UPDATE `ai_model_config` SET `config_json` = JSON_REMOVE(JSON_SET(`config_json`, '$.resource_id', 'volc.bigasr.sauc.duration'), '$.cluster') WHERE `id` = 'ASR_DoubaoStreamASR';

-- ==================== 豆包语音识别模型2.0 ====================

-- 插入豆包语音识别模型2.0配置
delete from `ai_model_config` where id = 'ASR_DoubaoStreamASRV2';
INSERT INTO `ai_model_config` VALUES ('ASR_DoubaoStreamASRV2', 'ASR', 'DoubaoStreamASRV2', '豆包语音识别模型2.0', 0, 1, '{
  "type": "doubao_stream",
  "appid": "",
  "access_token": "",
  "resource_id": "volc.seedasr.sauc.duration",
  "end_window_size": 200,
  "enable_multilingual": false,
  "language": "zh-CN",
  "output_dir": "tmp/"
}', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- 豆包语音识别模型2.0配置说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.volcengine.com/docs/6561/109979',
`remark` = '豆包语音识别模型2.0配置说明（基于火山引擎seed-asr）：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10038 开通豆包流式语音识别模型2.0
3. 在页面底部获取appid和access_token
4. 资源ID有两种：小时版（volc.seedasr.sauc.duration）和并发版（volc.seedasr.sauc.concurrent）
   - 小时版：固定为：volc.seedasr.sauc.duration（豆包语音识别模型2.0）
   - 并发版：固定为：volc.seedasr.sauc.concurrent（豆包语音识别模型2.0）

详细参数文档：https://www.volcengine.com/docs/6561/109979

注意：
- 豆包语音识别模型2.0使用volc.seedasr.sauc.duration资源ID，与豆包语音识别(流式)（volc.bigasr.sauc.duration）不同
- 语音识别模型2.0价格更为便宜，建议在高并发场景下使用并发版资源ID
' WHERE `id` = 'ASR_DoubaoStreamASRV2';
