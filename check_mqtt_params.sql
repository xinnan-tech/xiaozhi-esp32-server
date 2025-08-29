-- Check current MQTT-related parameters in sys_params table
SELECT * FROM sys_params WHERE param_code LIKE 'mqtt.%';

-- Check all system parameters to see what's configured
SELECT id, param_code, param_value, remark FROM sys_params ORDER BY id;