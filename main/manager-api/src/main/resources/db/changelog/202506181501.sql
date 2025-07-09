INSERT INTO `ai_model_config` (`id`, `model_type`, `model_code`, `model_name`, `is_default`,
                                                `is_enabled`, `config_json`, `doc_link`, `remark`, `sort`, `creator`,
                                                `create_date`, `updater`, `update_date`)
VALUES ('Memory_mem0_milvus', 'memory', 'mem0_milvus', 'Mem0AI本地记忆', 0, 1,
        '{\"llm\": {\"config\": {\"model\": \"qwen-plus\", \"top_p\": 1, \"api_key\": \"<your-apikey>\", \"max_tokens\": 2000, \"temperature\": 0.2, \"openai_base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\"}, \"provider\": \"openai\"}, \"type\": \"mem0_milvus\", \"embedder\": {\"config\": {\"model\": \"text-embedding-v4\", \"api_key\": \"<your-apikey>\", \"openai_base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1/\"}, \"provider\": \"openai\"}, \"vector_store\": {\"config\": {\"url\": \"http://127.0.0.1:19530\", \"collection_name\": \"mem0_collection\", \"embedding_model_dims\": 1024}, \"provider\": \"milvus\"}}',
        'https://app.mem0.ai/dashboard/get-started', 'Mem0AI记忆配置说明：\n1. 配置llm/embedder/vector_store\n', 3, NULL,
        NULL, 1, '2025-06-18 17:02:49');
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`,
                                                  `creator`, `create_date`, `updater`, `update_date`)
VALUES ('SYSTEM_Memory_mem0_milvus', 'Memory', 'mem0_milvus', 'mem0ai本地记忆',
        '[{\"key\": \"llm\", \"type\": \"dict\", \"label\": \"llm\", \"default\": \"\", \"editing\": false, \"selected\": false}, {\"key\": \"embedder\", \"type\": \"dict\", \"label\": \"embedder\", \"default\": \"\", \"editing\": false, \"selected\": false}, {\"key\": \"vector_store\", \"type\": \"dict\", \"label\": \"vector_store\", \"default\": \"\", \"editing\": false, \"selected\": false}]',
        0, 1, '2025-06-18 14:00:57', 1, '2025-06-18 14:00:57');
