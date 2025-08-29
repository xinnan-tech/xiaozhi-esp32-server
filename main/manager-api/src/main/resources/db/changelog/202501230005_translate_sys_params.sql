-- Translate system parameter remarks from Chinese to English

UPDATE sys_params 
SET remark = 'Time to disconnect when no voice input (seconds)'
WHERE param_code = 'close_connection_no_voice_time';

UPDATE sys_params 
SET remark = 'Wake word list for wake word recognition'
WHERE param_code = 'wakeup_words';

UPDATE sys_params 
SET remark = 'Home Assistant API key'
WHERE param_code = 'plugins.home_assistant.api_key';

-- Update any Chinese wake words to English equivalents (optional, can be customized by user)
UPDATE sys_params 
SET param_value = 'hello xiaozhi;hey xiaozhi;xiaozhi xiaozhi;hey assistant;hello assistant;wake up;listen to me;hey buddy'
WHERE param_code = 'wakeup_words' AND param_value LIKE '%你好小智%';

-- Translate column comments (if needed for documentation)
-- Note: These are database structure changes, not data changes
-- ALTER TABLE sys_params MODIFY COLUMN remark VARCHAR(255) COMMENT 'Parameter description';