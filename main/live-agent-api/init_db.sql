-- Active: 1763538755357@@127.0.0.1@5432@live_agent
-- Live Agent API Database Initialization Script
-- PostgreSQL 16

-- ==================== Extensions ====================
-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== Table: user ====================
-- User account table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Indexes for user table
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_userid ON "user"(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_username ON "user"(username);

-- Comments for user table
COMMENT ON TABLE "user" IS 'User account information';
COMMENT ON COLUMN "user".user_id IS 'External unique identifier (e.g., ULID)';
COMMENT ON COLUMN "user".username IS 'Unique username for login';
COMMENT ON COLUMN "user".password IS 'Hashed password';

-- ==================== Table: agents ====================
-- AI Agent configuration table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) UNIQUE NOT NULL,
    owner_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    description TEXT,
    voice_id VARCHAR(50),
    instruction TEXT NOT NULL,
    voice_opening TEXT,
    voice_closing TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_agents_owner FOREIGN KEY (owner_id) 
        REFERENCES "user"(user_id) ON DELETE CASCADE
);

-- Indexes for agents table
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_owner_id ON agents(owner_id);

-- Comments for agents table
COMMENT ON TABLE agents IS 'AI agent configurations';
COMMENT ON COLUMN agents.agent_id IS 'External unique identifier (e.g., ULID)';
COMMENT ON COLUMN agents.owner_id IS 'User ID of the agent owner';
COMMENT ON COLUMN agents.instruction IS 'System prompt/instruction for the agent';
COMMENT ON COLUMN agents.voice_opening IS 'Opening message when conversation starts';
COMMENT ON COLUMN agents.voice_closing IS 'Closing message when conversation ends';

-- ==================== Table: voices ====================
-- Voice configuration table
CREATE TABLE IF NOT EXISTS voices (
    id SERIAL PRIMARY KEY,
    voice_id VARCHAR(50) NOT NULL,
    owner_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    "desc" TEXT NOT NULL DEFAULT '',
    sample_url TEXT,
    sample_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_voices_owner FOREIGN KEY (owner_id) 
        REFERENCES "user"(user_id) ON DELETE CASCADE,
    CONSTRAINT uk_voices_owner_voice UNIQUE (voice_id, owner_id)
);

-- Indexes for voices table
CREATE INDEX IF NOT EXISTS idx_voices_voice_id ON voices(voice_id);
CREATE INDEX IF NOT EXISTS idx_voices_owner_id ON voices(owner_id);
CREATE INDEX IF NOT EXISTS idx_voices_created_at ON voices(created_at);

-- Comments for voices table
COMMENT ON TABLE voices IS 'Voice configurations for agents';
COMMENT ON COLUMN voices.voice_id IS 'Fish Audio voice ID';
COMMENT ON COLUMN voices.owner_id IS 'User ID of voice owner';
COMMENT ON COLUMN voices.name IS 'Voice display name';
COMMENT ON COLUMN voices."desc" IS 'Voice description';
COMMENT ON COLUMN voices.sample_url IS 'S3 URL of the original audio sample (for cloned voices)';
COMMENT ON COLUMN voices.sample_text IS 'Transcription text of the audio sample (for cloned voices)';

-- ==================== Table: agent_templates ====================
-- Pre-configured agent templates
CREATE TABLE IF NOT EXISTS agent_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    description TEXT,
    voice_id VARCHAR(50),
    instruction TEXT,
    voice_opening TEXT,
    voice_closing TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Indexes for agent_templates table
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_templates_template_id ON agent_templates(template_id);

-- Comments for agent_templates table
COMMENT ON TABLE agent_templates IS 'Pre-configured agent templates for quick setup';
COMMENT ON COLUMN agent_templates.template_id IS 'External unique identifier (e.g., ULID)';
COMMENT ON COLUMN agent_templates.voice_id IS 'Default voice ID for this template';

-- ==================== Table: chat_messages ====================
-- Chat messages table with unified content structure
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(50) UNIQUE NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    role SMALLINT NOT NULL CHECK (role IN (1, 2)),
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_chat_messages_agent FOREIGN KEY (agent_id) 
        REFERENCES agents(agent_id) ON DELETE CASCADE
);

-- Indexes for chat_messages table
-- Unique index for message_id (business key, used for API and S3 file naming)
CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_messages_message_id ON chat_messages(message_id);
-- Single-column index for agent filtering
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_id ON chat_messages(agent_id);
-- Composite index for cursor-based pagination (agent_id + message_id for efficient range queries)
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_message_composite ON chat_messages(agent_id, message_id);
-- GIN index for JSONB content search (future feature: search by message type, content, etc.)
CREATE INDEX IF NOT EXISTS idx_chat_messages_content_gin ON chat_messages USING GIN (content);

-- Comments for chat_messages table
COMMENT ON TABLE chat_messages IS 'Chat messages with unified content structure (text and S3 URLs)';
COMMENT ON COLUMN chat_messages.message_id IS 'External unique identifier (ULID) for API and S3 file naming';
COMMENT ON COLUMN chat_messages.agent_id IS 'Agent ID this message belongs to';
COMMENT ON COLUMN chat_messages.role IS 'Message role: 1=user, 2=agent';
COMMENT ON COLUMN chat_messages.content IS 'JSONB array: [{"message_type": "text|audio|image|file", "message_content": "text or S3 URL"}]';
COMMENT ON COLUMN chat_messages.created_at IS 'Message creation timestamp (UTC)';

-- ==================== Functions ====================
-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at on user table
CREATE TRIGGER update_user_updated_at
    BEFORE UPDATE ON "user"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create triggers for updated_at on agents table
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create triggers for updated_at on voices table
CREATE TRIGGER update_voices_updated_at
    BEFORE UPDATE ON voices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create triggers for updated_at on agent_templates table
CREATE TRIGGER update_agent_templates_updated_at
    BEFORE UPDATE ON agent_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== Table: memory_sharing ====================
-- Memory sharing configuration per user-agent
CREATE TABLE IF NOT EXISTS memory_sharing (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    share_type VARCHAR(20) NOT NULL CHECK (share_type IN ('none', 'specific', 'all')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uk_memory_sharing_user_agent UNIQUE (user_id, agent_id)
);

-- Indexes for memory_sharing table
CREATE INDEX IF NOT EXISTS idx_memory_sharing_user_id ON memory_sharing(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_sharing_agent_id ON memory_sharing(agent_id);
CREATE INDEX IF NOT EXISTS idx_memory_sharing_share_type ON memory_sharing(share_type);

-- Comments for memory_sharing table
COMMENT ON TABLE memory_sharing IS 'Memory sharing configuration per user-agent pair';
COMMENT ON COLUMN memory_sharing.user_id IS 'User who owns the memories';
COMMENT ON COLUMN memory_sharing.agent_id IS 'Source agent whose memories are being shared';
COMMENT ON COLUMN memory_sharing.share_type IS 'none=no sharing, specific=share with specific agents, all=share with all agents';

-- ==================== Table: memory_sharing_targets ====================
-- Target agents for specific sharing type
CREATE TABLE IF NOT EXISTS memory_sharing_targets (
    id SERIAL PRIMARY KEY,
    sharing_id INT NOT NULL,
    target_agent_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_memory_sharing_targets_sharing FOREIGN KEY (sharing_id)
        REFERENCES memory_sharing(id) ON DELETE CASCADE,
    CONSTRAINT uk_memory_sharing_targets UNIQUE (sharing_id, target_agent_id)
);

-- Indexes for memory_sharing_targets table
CREATE INDEX IF NOT EXISTS idx_memory_sharing_targets_sharing_id ON memory_sharing_targets(sharing_id);
CREATE INDEX IF NOT EXISTS idx_memory_sharing_targets_target_agent_id ON memory_sharing_targets(target_agent_id);

-- Comments for memory_sharing_targets table
COMMENT ON TABLE memory_sharing_targets IS 'Target agents for specific memory sharing';
COMMENT ON COLUMN memory_sharing_targets.sharing_id IS 'Reference to memory_sharing record';
COMMENT ON COLUMN memory_sharing_targets.target_agent_id IS 'Agent ID that can access the shared memories';

-- Create triggers for updated_at on memory_sharing table
CREATE TRIGGER update_memory_sharing_updated_at
    BEFORE UPDATE ON memory_sharing
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==================== Grant Permissions ====================
-- Grant necessary permissions to postgres user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ==================== Initialization Complete ====================
-- Database schema initialization completed successfully

