insert ignore into `sys_params`
  (id, param_code, param_value, value_type, param_type, remark)
values
  (775, 'protocols.enabled_protocols', '["websocket"]', 'string', 1, '启用的协议列表'),
  (776, 'protocols.websocket_enabled', 'true', 'boolean', 1, 'WebSocket协议开关'),
  (777, 'protocols.mqtt_enabled', 'false', 'boolean', 1, 'MQTT协议开关'),
  (778, 'mqtt_server.enabled', 'false', 'boolean', 1, '是否启用MQTT服务器'),
  (779, 'mqtt_server.host', '0.0.0.0', 'string', 1, 'MQTT服务器监听地址'),
  (780, 'mqtt_server.port', '1883', 'number', 1, 'MQTT服务器端口'),
  (781, 'mqtt_server.udp_port', '1883', 'number', 1, 'UDP音频端口'),
  (782, 'mqtt_server.public_endpoint', '127.0.0.1', 'string', 1, 'MQTT公网/局域网访问地址'),
  (783, 'mqtt_server.max_connections', '1000', 'number', 1, '最大连接数'),
  (784, 'mqtt_server.heartbeat_interval', '30', 'number', 1, '心跳间隔(秒)'),
  (785, 'mqtt_server.max_payload_size', '8192', 'number', 1, '最大消息大小'),
  (786, 'mqtt_server.signature_key', 'null', 'string', 1, 'MQTT签名密钥');
