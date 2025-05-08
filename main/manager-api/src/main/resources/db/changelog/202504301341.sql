update `ai_model_provider` set `fields` = 
'[{"key": "api_url","label": "API地址","type": "string"},{"key": "voice","label": "音色","type": "string"},{"key": "output_dir","label": "输出目录","type": "string"},{"key": "authorization","label": "授权","type": "string"},{"key": "appid","label": "应用ID","type": "string"},{"key": "access_token","label": "访问令牌","type": "string"},{"key": "cluster","label": "集群","type": "string"},{"key": "speed_ratio","label": "语速","type": "number"},{"key": "volume_ratio","label": "音量","type": "number"},{"key": "pitch_ratio","label": "音高","type": "number"}]'
where `id` = 'SYSTEM_TTS_doubao';

-- 添加阿里云ASR供应器
delete from `ai_model_provider` where `id` = 'SYSTEM_ASR_AliyunASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_AliyunASR', 'ASR', 'aliyun', '阿里云语音识别', '[{"key":"appkey","label":"应用AppKey","type":"string"},{"key":"token","label":"临时Token","type":"string"},{"key":"access_key_id","label":"AccessKey ID","type":"string"},{"key":"access_key_secret","label":"AccessKey Secret","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 5, 1, NOW(), 1, NOW());

-- 添加阿里云ASR模型配置
delete from `ai_model_config` where `id` = 'ASR_AliyunASR';
INSERT INTO `ai_model_config` VALUES ('ASR_AliyunASR', 'ASR', 'AliyunASR', '阿里云语音识别', 0, 1, '{\"type\": \"aliyun\", \"appkey\": \"\", \"token\": \"\", \"access_key_id\": \"\", \"access_key_secret\": \"\", \"output_dir\": \"tmp/\"}', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- 更新阿里云ASR模型配置的说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云ASR配置说明：
1. 访问 https://nls-portal.console.aliyun.com/ 开通服务
2. 访问 https://nls-portal.console.aliyun.com/applist 获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取token
4. 获取access_key_id和access_key_secret
5. 填入配置文件中' WHERE `id` = 'ASR_AliyunASR';

-- 插入固件类型字典类型
delete from `sys_dict_type` where `id` = 101;
INSERT INTO `sys_dict_type` (`id`, `dict_type`, `dict_name`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(101, 'FIRMWARE_TYPE', '固件类型', '固件类型字典', 0, 1, NOW(), 1, NOW());

-- 插入固件类型字典数据
delete from `sys_dict_data` where `dict_type_id` = 101;
INSERT INTO `sys_dict_data` (`id`, `dict_type_id`, `dict_label`, `dict_value`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(101001, 101, '面包板新版接线（WiFi）', 'bread-compact-wifi', '面包板新版接线（WiFi）', 1, 1, NOW(), 1, NOW()),
(101002, 101, '面包板新版接线（WiFi）+ LCD', 'bread-compact-wifi-lcd', '面包板新版接线（WiFi）+ LCD', 2, 1, NOW(), 1, NOW()),
(101003, 101, '面包板新版接线（ML307 AT）', 'bread-compact-ml307', '面包板新版接线（ML307 AT）', 3, 1, NOW(), 1, NOW()),
(101004, 101, '面包板（WiFi） ESP32 DevKit', 'bread-compact-esp32', '面包板（WiFi） ESP32 DevKit', 4, 1, NOW(), 1, NOW()),
(101005, 101, '面包板（WiFi+ LCD） ESP32 DevKit', 'bread-compact-esp32-lcd', '面包板（WiFi+ LCD） ESP32 DevKit', 5, 1, NOW(), 1, NOW()),
(101006, 101, 'DFRobot 行空板 k10', 'df-k10', 'DFRobot 行空板 k10', 6, 1, NOW(), 1, NOW()),
(101007, 101, 'ESP32 CGC', 'esp32-cgc', 'ESP32 CGC', 7, 1, NOW(), 1, NOW()),
(101008, 101, 'ESP BOX 3', 'esp-box-3', 'ESP BOX 3', 8, 1, NOW(), 1, NOW()),
(101009, 101, 'ESP BOX', 'esp-box', 'ESP BOX', 9, 1, NOW(), 1, NOW()),
(101010, 101, 'ESP BOX Lite', 'esp-box-lite', 'ESP BOX Lite', 10, 1, NOW(), 1, NOW()),
(101011, 101, 'Kevin Box 1', 'kevin-box-1', 'Kevin Box 1', 11, 1, NOW(), 1, NOW()),
(101012, 101, 'Kevin Box 2', 'kevin-box-2', 'Kevin Box 2', 12, 1, NOW(), 1, NOW()),
(101013, 101, 'Kevin C3', 'kevin-c3', 'Kevin C3', 13, 1, NOW(), 1, NOW()),
(101014, 101, 'Kevin SP V3开发板', 'kevin-sp-v3-dev', 'Kevin SP V3开发板', 14, 1, NOW(), 1, NOW()),
(101015, 101, 'Kevin SP V4开发板', 'kevin-sp-v4-dev', 'Kevin SP V4开发板', 15, 1, NOW(), 1, NOW()),
(101016, 101, '鱼鹰科技3.13LCD开发板', 'kevin-yuying-313lcd', '鱼鹰科技3.13LCD开发板', 16, 1, NOW(), 1, NOW()),
(101017, 101, '立创·实战派ESP32-S3开发板', 'lichuang-dev', '立创·实战派ESP32-S3开发板', 17, 1, NOW(), 1, NOW()),
(101018, 101, '立创·实战派ESP32-C3开发板', 'lichuang-c3-dev', '立创·实战派ESP32-C3开发板', 18, 1, NOW(), 1, NOW()),
(101019, 101, '神奇按钮 Magiclick_2.4', 'magiclick-2p4', '神奇按钮 Magiclick_2.4', 19, 1, NOW(), 1, NOW()),
(101020, 101, '神奇按钮 Magiclick_2.5', 'magiclick-2p5', '神奇按钮 Magiclick_2.5', 20, 1, NOW(), 1, NOW()),
(101021, 101, '神奇按钮 Magiclick_C3', 'magiclick-c3', '神奇按钮 Magiclick_C3', 21, 1, NOW(), 1, NOW()),
(101022, 101, '神奇按钮 Magiclick_C3_v2', 'magiclick-c3-v2', '神奇按钮 Magiclick_C3_v2', 22, 1, NOW(), 1, NOW()),
(101023, 101, 'M5Stack CoreS3', 'm5stack-core-s3', 'M5Stack CoreS3', 23, 1, NOW(), 1, NOW()),
(101024, 101, 'AtomS3 + Echo Base', 'atoms3-echo-base', 'AtomS3 + Echo Base', 24, 1, NOW(), 1, NOW()),
(101025, 101, 'AtomS3R + Echo Base', 'atoms3r-echo-base', 'AtomS3R + Echo Base', 25, 1, NOW(), 1, NOW()),
(101026, 101, 'AtomS3R CAM/M12 + Echo Base', 'atoms3r-cam-m12-echo-base', 'AtomS3R CAM/M12 + Echo Base', 26, 1, NOW(), 1, NOW()),
(101027, 101, 'AtomMatrix + Echo Base', 'atommatrix-echo-base', 'AtomMatrix + Echo Base', 27, 1, NOW(), 1, NOW()),
(101028, 101, '虾哥 Mini C3', 'xmini-c3', '虾哥 Mini C3', 28, 1, NOW(), 1, NOW()),
(101029, 101, 'ESP32S3_KORVO2_V3开发板', 'esp32s3-korvo2-v3', 'ESP32S3_KORVO2_V3开发板', 29, 1, NOW(), 1, NOW()),
(101030, 101, 'ESP-SparkBot开发板', 'esp-sparkbot', 'ESP-SparkBot开发板', 30, 1, NOW(), 1, NOW()),
(101031, 101, 'ESP-Spot-S3', 'esp-spot-s3', 'ESP-Spot-S3', 31, 1, NOW(), 1, NOW()),
(101032, 101, 'Waveshare ESP32-S3-Touch-AMOLED-1.8', 'esp32-s3-touch-amoled-1.8', 'Waveshare ESP32-S3-Touch-AMOLED-1.8', 32, 1, NOW(), 1, NOW()),
(101033, 101, 'Waveshare ESP32-S3-Touch-LCD-1.85C', 'esp32-s3-touch-lcd-1.85c', 'Waveshare ESP32-S3-Touch-LCD-1.85C', 33, 1, NOW(), 1, NOW()),
(101034, 101, 'Waveshare ESP32-S3-Touch-LCD-1.85', 'esp32-s3-touch-lcd-1.85', 'Waveshare ESP32-S3-Touch-LCD-1.85', 34, 1, NOW(), 1, NOW()),
(101035, 101, 'Waveshare ESP32-S3-Touch-LCD-1.46', 'esp32-s3-touch-lcd-1.46', 'Waveshare ESP32-S3-Touch-LCD-1.46', 35, 1, NOW(), 1, NOW()),
(101036, 101, 'Waveshare ESP32-S3-Touch-LCD-3.5', 'esp32-s3-touch-lcd-3.5', 'Waveshare ESP32-S3-Touch-LCD-3.5', 36, 1, NOW(), 1, NOW()),
(101037, 101, '土豆子', 'tudouzi', '土豆子', 37, 1, NOW(), 1, NOW()),
(101038, 101, 'LILYGO T-Circle-S3', 'lilygo-t-circle-s3', 'LILYGO T-Circle-S3', 38, 1, NOW(), 1, NOW()),
(101039, 101, 'LILYGO T-CameraPlus-S3', 'lilygo-t-cameraplus-s3', 'LILYGO T-CameraPlus-S3', 39, 1, NOW(), 1, NOW()),
(101040, 101, 'Movecall Moji 小智AI衍生版', 'movecall-moji-esp32s3', 'Movecall Moji 小智AI衍生版', 40, 1, NOW(), 1, NOW()),
(101041, 101, 'Movecall CuiCan 璀璨·AI吊坠', 'movecall-cuican-esp32s3', 'Movecall CuiCan 璀璨·AI吊坠', 41, 1, NOW(), 1, NOW()),
(101042, 101, '正点原子DNESP32S3开发板', 'atk-dnesp32s3', '正点原子DNESP32S3开发板', 42, 1, NOW(), 1, NOW()),
(101043, 101, '正点原子DNESP32S3-BOX', 'atk-dnesp32s3-box', '正点原子DNESP32S3-BOX', 43, 1, NOW(), 1, NOW()),
(101044, 101, '嘟嘟开发板CHATX(wifi)', 'du-chatx', '嘟嘟开发板CHATX(wifi)', 44, 1, NOW(), 1, NOW()),
(101045, 101, '太极小派esp32s3', 'taiji-pi-s3', '太极小派esp32s3', 45, 1, NOW(), 1, NOW()),
(101046, 101, '无名科技星智0.85(WIFI)', 'xingzhi-cube-0.85tft-wifi', '无名科技星智0.85(WIFI)', 46, 1, NOW(), 1, NOW()),
(101047, 101, '无名科技星智0.85(ML307)', 'xingzhi-cube-0.85tft-ml307', '无名科技星智0.85(ML307)', 47, 1, NOW(), 1, NOW()),
(101048, 101, '无名科技星智0.96(WIFI)', 'xingzhi-cube-0.96oled-wifi', '无名科技星智0.96(WIFI)', 48, 1, NOW(), 1, NOW()),
(101049, 101, '无名科技星智0.96(ML307)', 'xingzhi-cube-0.96oled-ml307', '无名科技星智0.96(ML307)', 49, 1, NOW(), 1, NOW()),
(101050, 101, '无名科技星智1.54(WIFI)', 'xingzhi-cube-1.54tft-wifi', '无名科技星智1.54(WIFI)', 50, 1, NOW(), 1, NOW()),
(101051, 101, '无名科技星智1.54(ML307)', 'xingzhi-cube-1.54tft-ml307', '无名科技星智1.54(ML307)', 51, 1, NOW(), 1, NOW()),
(101052, 101, 'SenseCAP Watcher', 'sensecap-watcher', 'SenseCAP Watcher', 52, 1, NOW(), 1, NOW()),
(101053, 101, '四博智联AI陪伴盒子', 'doit-s3-aibox', '四博智联AI陪伴盒子', 53, 1, NOW(), 1, NOW()),
(101054, 101, '元控·青春', 'mixgo-nova', '元控·青春', 54, 1, NOW(), 1, NOW());
