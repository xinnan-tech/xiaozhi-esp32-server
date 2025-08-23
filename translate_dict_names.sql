-- Translate Chinese dictionary type names to English
-- Run this SQL in your Railway MySQL database

USE railway;

-- Update dictionary type names from Chinese to English
UPDATE `sys_dict_type` SET `dict_name` = 'Mobile Area' WHERE `dict_type` = 'MOBILE_AREA';
UPDATE `sys_dict_type` SET `dict_name` = 'Firmware Type' WHERE `dict_type` = 'FIRMWARE_TYPE';

-- Also update remarks to English
UPDATE `sys_dict_type` SET `remark` = 'Mobile area codes dictionary' WHERE `dict_type` = 'MOBILE_AREA';
UPDATE `sys_dict_type` SET `remark` = 'Firmware types dictionary' WHERE `dict_type` = 'FIRMWARE_TYPE';

-- Verify the changes
SELECT id, dict_type, dict_name, remark FROM sys_dict_type WHERE dict_type IN ('MOBILE_AREA', 'FIRMWARE_TYPE');