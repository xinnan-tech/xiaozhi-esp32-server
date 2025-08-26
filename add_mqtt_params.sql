-- Add MQTT configuration parameters to sys_params table
-- Replace the values with your actual MQTT broker configuration

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) 
VALUES (120, 'mqtt.broker', '139.59.7.72', 'string', 1, 'MQTT broker IP address');

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) 
VALUES (121, 'mqtt.port', '1883', 'string', 1, 'MQTT broker port');

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) 
VALUES (122, 'mqtt.signature_key', 'your-secure-signature-key-here', 'string', 1, 'MQTT signature key for authentication');