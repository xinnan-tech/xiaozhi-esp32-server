-- Add semantic search configuration for improved music search functionality
-- 添加语义搜索配置以改进音乐搜索功能

-- Delete existing semantic search params if they exist
delete from sys_params where id in (701, 702, 703, 704, 705, 706, 707);

-- Insert semantic search configuration parameters
INSERT INTO sys_params
(id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date)
VALUES
(701, 'semantic_search.enabled', 'true', 'boolean', 1, 'Enable semantic music search using vector embeddings', NULL, NULL, NULL, NULL),
(702, 'semantic_search.qdrant_url', 'https://a2482b9f-2c29-476e-9ff0-741aaaaf632e.eu-west-1-0.aws.cloud.qdrant.io', 'string', 1, 'Qdrant vector database URL for music embeddings', NULL, NULL, NULL, NULL),
(703, 'semantic_search.qdrant_api_key', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zPBGAqVGy-edbbgfNOJsPWV496BsnQ4ELOFvsLNyjsk', 'string', 1, 'Qdrant API key for authentication', NULL, NULL, NULL, NULL),
(704, 'semantic_search.collection_name', 'xiaozhi_music', 'string', 1, 'Vector collection name for music embeddings', NULL, NULL, NULL, NULL),
(705, 'semantic_search.embedding_model', 'all-MiniLM-L6-v2', 'string', 1, 'Sentence transformer model for generating embeddings', NULL, NULL, NULL, NULL),
(706, 'semantic_search.search_limit', '5', 'number', 1, 'Maximum number of search results to return', NULL, NULL, NULL, NULL),
(707, 'semantic_search.min_score_threshold', '0.5', 'number', 1, 'Minimum similarity score threshold (0.0-1.0)', NULL, NULL, NULL, NULL);