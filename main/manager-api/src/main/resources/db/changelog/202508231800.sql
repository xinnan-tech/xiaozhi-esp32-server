-- Create parent_profile table for mobile app user profiles
-- This table stores additional profile information for parents using the mobile app

CREATE TABLE parent_profile (
    id bigint NOT NULL COMMENT 'Primary key ID',
    user_id bigint NOT NULL COMMENT 'Foreign key to sys_user table',
    supabase_user_id varchar(255) COMMENT 'Supabase user ID for reference',
    full_name varchar(255) COMMENT 'Parent full name',
    email varchar(255) COMMENT 'Parent email address',
    phone_number varchar(50) COMMENT 'Parent phone number',
    preferred_language varchar(10) DEFAULT 'en' COMMENT 'Preferred language code (en, es, fr, etc.)',
    timezone varchar(100) DEFAULT 'UTC' COMMENT 'User timezone',
    notification_preferences JSON COMMENT 'JSON object with notification settings',
    onboarding_completed tinyint(1) DEFAULT 0 COMMENT 'Whether onboarding is completed',
    terms_accepted_at datetime COMMENT 'When terms of service were accepted',
    privacy_policy_accepted_at datetime COMMENT 'When privacy policy was accepted',
    creator bigint COMMENT 'User who created this record',
    create_date datetime DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updater bigint COMMENT 'User who last updated this record',
    update_date datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id),
    UNIQUE KEY uk_supabase_user_id (supabase_user_id),
    FOREIGN KEY fk_parent_profile_user_id (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
    INDEX idx_email (email),
    INDEX idx_phone_number (phone_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Parent profile table for mobile app users';