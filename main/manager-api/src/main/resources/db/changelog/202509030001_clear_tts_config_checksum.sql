-- Clear checksum for the modified TTS configuration changeset
-- This allows the updated changeset with placeholder API keys to be applied
-- -------------------------------------------------------------------------

-- Clear the checksum for the modified changeset 202509020005
UPDATE DATABASECHANGELOG 
SET MD5SUM = NULL 
WHERE ID = '202509020005' AND AUTHOR = 'claude';