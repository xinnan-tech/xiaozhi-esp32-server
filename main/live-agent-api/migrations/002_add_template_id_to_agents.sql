-- Migration: Add template_id to agents table
-- Purpose: Track which template an agent was created from, enabling template filtering

-- Step 1: Add template_id column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS template_id VARCHAR(50);

-- Step 2: Add index for efficient querying
CREATE INDEX IF NOT EXISTS idx_agents_template_id ON agents(template_id);

-- Step 3: Backfill historical data by matching agent name with template name
-- This updates existing agents that were created from templates
UPDATE agents a
SET template_id = t.template_id
FROM agent_templates t
WHERE a.name = t.name 
  AND a.template_id IS NULL;

-- Note: Foreign key constraint is intentionally omitted
-- This allows templates to be deleted without affecting agents

