-- 本文件用于初始化系统参数数据，无需手动执行，在项目启动时会自动执行
-- --------------------------------------------------------
-- 初始化参数管理配置
DROP TABLE IF EXISTS sys_params;
-- 参数管理
create table sys_params
(
  id                   bigint NOT NULL COMMENT 'id',
  param_code           varchar(100) COMMENT '参数编码',
  param_value          varchar(2000) COMMENT '参数值',
  param_type           tinyint unsigned default 1 COMMENT '类型   0：系统参数   1：非系统参数',
  remark               varchar(200) COMMENT '备注',
  creator              bigint COMMENT '创建者',
  create_date          datetime COMMENT '创建时间',
  updater              bigint COMMENT '更新者',
  update_date          datetime COMMENT '更新时间',
  primary key (id),
  unique key uk_param_code (param_code)
)ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COMMENT='参数管理';

-- 服务器配置
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (1, 'server.ip', '0.0.0.0', 1, '服务器监听IP地址');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (2, 'server.port', '8000', 1, '服务器监听端口');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (3, 'server.secret', 'null', 1, '服务器密钥');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (4, 'log.log_format', '<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{selected_module}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>', 1, '控制台日志格式');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (5, 'log.log_format_file', '{time:YYYY-MM-DD HH:mm:ss} - {version}_{selected_module} - {name} - {level} - {extra[tag]} - {message}', 1, '文件日志格式');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (6, 'log.log_level', 'INFO', 1, '日志级别');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (7, 'log.log_dir', 'tmp', 1, '日志目录');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (8, 'log.log_file', 'server.log', 1, '日志文件名');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (9, 'log.data_dir', 'data', 1, '数据目录');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (10, 'delete_audio', 'true', 1, '是否删除使用后的音频文件');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (11, 'close_connection_no_voice_time', '120', 1, '无语音输入断开连接时间(秒)');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (12, 'tts_timeout', '10', 1, 'TTS请求超时时间(秒)');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (13, 'enable_wakeup_words_response_cache', 'true', 1, '是否开启唤醒词加速');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (14, 'enable_greeting', 'true', 1, '是否开启开场回复');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (15, 'enable_stop_tts_notify', 'false', 1, '是否开启结束提示音');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (16, 'stop_tts_notify_voice', 'config/assets/tts_notify.mp3', 1, '结束提示音文件路径');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (17, 'exit_commands', '["退出","关闭"]', 1, '退出命令列表');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (18, 'xiaozhi', '{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}', 1, '小智类型');
INSERT INTO `sys_params` (id, param_code, param_value, param_type, remark) VALUES (19, 'wakeup_words', '["你好小智","你好小志","小爱同学","你好小鑫","你好小新","小美同学","小龙小龙","喵喵同学","小滨小滨","小冰小冰"]', 1, '唤醒词列表');
