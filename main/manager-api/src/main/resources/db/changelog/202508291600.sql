-- Content Library Table for Music and Stories
-- Author: System
-- Date: 2025-08-29
-- Description: Creates table to store music and story content metadata for the mobile app library

CREATE TABLE content_library (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    romanized VARCHAR(255),
    filename VARCHAR(255) NOT NULL,
    content_type ENUM('music', 'story') NOT NULL,
    category VARCHAR(50) NOT NULL,
    alternatives TEXT COMMENT 'JSON array of alternative search terms',
    aws_s3_url VARCHAR(500) COMMENT 'S3 URL for the audio file',
    duration_seconds INT DEFAULT NULL COMMENT 'Duration in seconds',
    file_size_bytes BIGINT DEFAULT NULL COMMENT 'File size in bytes',
    is_active TINYINT(1) DEFAULT 1 COMMENT '1=active, 0=inactive',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_content_type_category (content_type, category),
    INDEX idx_title (title),
    INDEX idx_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Content library for music and stories available on devices';