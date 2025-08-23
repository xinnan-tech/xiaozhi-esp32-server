-- Translate Chinese dictionary type names to English
UPDATE `sys_dict_type` SET `dict_name` = 'Mobile Area' WHERE `dict_type` = 'MOBILE_AREA';
UPDATE `sys_dict_type` SET `dict_name` = 'Firmware Type' WHERE `dict_type` = 'FIRMWARE_TYPE';

-- Also update remarks to English
UPDATE `sys_dict_type` SET `remark` = 'Mobile area codes dictionary' WHERE `dict_type` = 'MOBILE_AREA';
UPDATE `sys_dict_type` SET `remark` = 'Firmware types dictionary' WHERE `dict_type` = 'FIRMWARE_TYPE';