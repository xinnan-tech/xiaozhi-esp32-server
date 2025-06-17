-- 智控台开启唤醒词加速
update `sys_params` set param_value = '你好小智;你好小志;小爱同学;你好小鑫;你好小新;小美同学;小龙小龙;喵喵同学;小滨小滨;小冰小冰;嘿你好呀' where param_code = 'wakeup_words';
update `sys_params` set param_value = 'true' where param_code = 'enable_wakeup_words_response_cache';
