insert ignore into `sys_params`
  (id, param_code, param_value, value_type, param_type, remark)
values
  (793, 'mqtt_server.manager_api', 'null', 'string', 1, '原生MQTT管理API地址'),
  (794, 'mqtt_server.manager_api_secret', 'null', 'string', 1, '原生MQTT管理API签名密钥');

update `sys_params`
set param_value = '',
    remark = 'MQTT公网/局域网访问地址（需配置为设备可达地址）'
where param_code = 'mqtt_server.public_endpoint'
  and param_value = '127.0.0.1';
