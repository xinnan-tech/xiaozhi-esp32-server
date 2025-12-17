-- Migration: Add message_time column to chat_messages table
-- Purpose: Support correct message ordering based on when message actually occurred

-- Step 1: Add message_time column (nullable first for existing data)
ALTER TABLE chat_messages 
ADD COLUMN IF NOT EXISTS message_time TIMESTAMPTZ;

-- Step 2: Backfill existing data - use created_at as message_time for historical records
UPDATE chat_messages 
SET message_time = created_at 
WHERE message_time IS NULL;

-- Step 3: Set NOT NULL constraint and default value
ALTER TABLE chat_messages 
ALTER COLUMN message_time SET NOT NULL,
ALTER COLUMN message_time SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

-- Step 4: Create index for efficient ordering queries
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_message_time 
ON chat_messages(agent_id, message_time);

-- Step 5: Add column comment
COMMENT ON COLUMN chat_messages.message_time IS 'When message actually occurred (for correct ordering)';

-- Migration completed

