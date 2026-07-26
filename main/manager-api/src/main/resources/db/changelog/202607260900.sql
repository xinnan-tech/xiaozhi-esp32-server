insert ignore into `sys_params`
  (id, param_code, param_value, value_type, param_type, remark)
values
  (787, 'mqtt_server.udp_bind_host', '', 'string', 1, 'UDP音频监听地址（留空时自动选择）'),
  (788, 'mqtt_server.message_queue_size', '128', 'number', 1, 'MQTT应用消息队列上限'),
  (789, 'mqtt_server.business_ready_timeout', '30', 'number', 1, 'Hello等待业务运行时就绪超时(秒)'),
  (790, 'mqtt_server.max_pending_connections', '128', 'number', 1, 'MQTT待认证连接上限'),
  (791, 'mqtt_server.goodbye_timeout', '1', 'number', 1, 'MQTT goodbye发送超时(秒)'),
  (792, 'mqtt_server.close_timeout', '2', 'number', 1, 'MQTT连接清理超时(秒)');
