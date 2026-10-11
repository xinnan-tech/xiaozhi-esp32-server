-- Westernize upstream seeds reintroduced by the re-registered upstream
-- queue (202606231030..202609172100). Append-only: follow-up cleanup for
-- Chinese-facing rows added by upstream changesets, per downstream policy.

-- EdgeTTS provider fields and remark were overwritten with Chinese labels.
UPDATE `ai_model_provider`
SET `fields` = '[{"key":"voice","label":"Voice","type":"string"},{"key":"output_dir","label":"Output directory","type":"string"},{"key":"rate","label":"Rate (-100~100)","type":"number"},{"key":"volume","label":"Volume (0~100)","type":"number"},{"key":"pitch","label":"Pitch (-100~100)","type":"number"}]'
WHERE `id` = 'SYSTEM_TTS_edge';

UPDATE `ai_model_config`
SET `remark` = 'EdgeTTS configuration:
1. Uses the Microsoft Edge TTS service
2. Supports many languages and voices
3. Free to use, no registration required
4. Requires network access
5. Output files are saved in the tmp/ directory
6. Rate: -100~100, 0 is normal speed
7. Volume: 0~100, 50 is normal volume
8. Pitch: -100~100, 0 is normal pitch'
WHERE `id` = 'TTS_EdgeTTS';

-- Minimax streaming TTS voices (Chinese provider) seeded for a provider that
-- does not exist downstream.
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_MinimaxStreamTTS';
DELETE FROM `ai_model_config` WHERE `id` = 'TTS_MinimaxStreamTTS';
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_TTS_MinimaxStreamTTS';

-- Hass state plugin (upstream unified get/set into one plugin): English
-- display name and field labels.
UPDATE `ai_model_provider`
SET `name` = 'HomeAssistant Device Control',
    `fields` = JSON_SET(
        `fields`,
        '$[0].label', 'HA server URL',
        '$[1].label', 'HA API access token',
        '$[2].label', 'Device list (name,entity_id;...)'
    )
WHERE `id` = 'SYSTEM_PLUGIN_HA_STATE';

-- Web search: upstream re-set the provider label in Chinese and the seed
-- still defaults to the China-only metaso provider. Tavily is the western
-- default; metaso remains selectable for users who want it.
UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    '$[0].label', 'Search provider: tavily / serply / metaso',
    '$[0].default', 'tavily',
    '$[3].default', 'tvly-XXXX'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEB_SEARCH';

-- News plugin: the seed queue carried feeds.reuters.com URLs, but Reuters
-- shut its public RSS down in 2020, so every fetch fell through to fallback.
-- Point the stored defaults at live western feeds (matches the server-side
-- get_news.py built-in sources).
UPDATE `sys_params`
SET `param_value` = 'https://feeds.bbci.co.uk/news/world/rss.xml'
WHERE `param_code` = 'plugins.get_news.default_rss_url';

UPDATE `sys_params`
SET `param_value` = '{"world":"https://feeds.bbci.co.uk/news/world/rss.xml","technology":"https://techcrunch.com/feed/","business":"https://feeds.bbci.co.uk/news/business/rss.xml"}'
WHERE `param_code` = 'plugins.get_news.category_urls';

UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    '$[0].default', 'https://feeds.bbci.co.uk/news/world/rss.xml',
    '$[0].description', 'Fallback RSS URL when built-in sources fail. Built-in sources include BBC, CNN, NPR, Guardian, TechCrunch and Ars Technica.'
)
WHERE `id` = 'SYSTEM_PLUGIN_NEWS';

-- Home Assistant demo devices referenced China-region cloud switches
-- (cuco_cn / iot_cn entity ids). Use neutral example entity ids instead.
UPDATE `sys_params`
SET `param_value` = 'Living Room,Toy Light,switch.living_room_toy_light;Bedroom,Table Lamp,switch.bedroom_table_lamp'
WHERE `param_code` = 'plugins.home_assistant.devices';
