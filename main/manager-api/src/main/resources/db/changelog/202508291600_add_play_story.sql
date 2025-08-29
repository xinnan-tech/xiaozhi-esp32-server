-- Add play_story plugin support
-- This adds play_story to all agents that currently have play_music

-- 1. Add play_story plugin provider
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_PLUGIN_STORY';
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields, sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_STORY', 'Plugin', 'play_story', 'Story Playback', JSON_ARRAY(), 25, 0, NOW(), 0, NOW());

-- 2. Add play_story to all agents that have play_music
INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
SELECT DISTINCT m.agent_id, 'SYSTEM_PLUGIN_STORY', '{}'
FROM ai_agent_plugin_mapping m
JOIN ai_model_provider p ON p.id = m.plugin_id
WHERE p.provider_code = 'play_music'
  AND NOT EXISTS (
    SELECT 1 FROM ai_agent_plugin_mapping m2
    JOIN ai_model_provider p2 ON p2.id = m2.plugin_id
    WHERE m2.agent_id = m.agent_id AND p2.provider_code = 'play_story'
  );

-- 3. Add optional configuration fields for play_story
UPDATE `ai_model_provider` SET 
fields = JSON_ARRAY(
    JSON_OBJECT('key', 'story_dir', 'type', 'string', 'label', 'Story Directory', 'default', './stories'),
    JSON_OBJECT('key', 'story_ext', 'type', 'array', 'label', 'Story File Extensions', 'default', '.mp3;.wav;.p3'),
    JSON_OBJECT('key', 'refresh_time', 'type', 'number', 'label', 'Refresh Time (seconds)', 'default', '300')
)
WHERE id = 'SYSTEM_PLUGIN_STORY';
