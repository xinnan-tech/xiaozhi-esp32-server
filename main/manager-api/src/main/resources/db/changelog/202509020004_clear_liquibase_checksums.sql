-- Clear Liquibase checksums for modified changesets
-- This allows the updated TTS configurations to be applied
-- -------------------------------------------------------

-- Update the checksum for the modified changeset
UPDATE DATABASECHANGELOG 
SET MD5SUM = NULL 
WHERE ID = '202509020001' AND AUTHOR = 'claude';

-- Clear any locks
DELETE FROM DATABASECHANGELOGLOCK WHERE ID = 1;
INSERT INTO DATABASECHANGELOGLOCK (ID, LOCKED, LOCKGRANTED, LOCKEDBY) VALUES (1, 0, NULL, NULL);