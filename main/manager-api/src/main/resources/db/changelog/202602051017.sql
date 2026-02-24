-- 新增powermem记忆模型供应器
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES ('SYSTEM_Memory_powermem', 'Memory', 'powermem', 'PowerMem记忆', '[
  {"key":"enable_user_profile","label":"启用用户画像","type":"boolean"},
  {"key":"llm_provider","label":"LLM提供商","type":"string"},
  {"key":"llm_api_key","label":"LLM API密钥","type":"string"},
  {"key":"llm_model","label":"LLM模型","type":"string"},
  {"key":"openai_base_url","label":"OpenAI基础URL","type":"string"},
  {"key":"embedding_provider","label":"Embedding提供商","type":"string"},
  {"key":"embedding_api_key","label":"Embedding API密钥","type":"string"},
  {"key":"embedding_model","label":"Embedding模型","type":"string"},
  {"key":"embedding_openai_base_url","label":"Embedding OpenAI基础URL","type":"string"},
  {"key":"embedding_dims","label":"Embedding维度","type":"integer"},
  {"key":"vector_store","label":"向量存储配置(JSON)","type":"dict"}
]', 4, 1, NOW(), 1, NOW());

-- 新增PowerMem记忆模型配置
INSERT INTO `ai_model_config` VALUES (
  'Memory_powermem',
  'Memory',
  'powermem',
  'PowerMem记忆',
  0,
  1,
  '{\"type\": \"powermem\", \"enable_user_profile\": true, \"llm_provider\": \"openai\", \"llm_api_key\": \"你的LLM API密钥\", \"llm_model\": \"qwen-plus\", \"openai_base_url\": \"\", \"embedding_provider\": \"openai\", \"embedding_api_key\": \"你的嵌入模型API密钥\", \"embedding_model\": \"text-embedding-v4\", \"embedding_openai_base_url\": \"https://api.openai.com/v1\", \"embedding_dims\": \"\", \"vector_store\": {\"provider\": \"sqlite\", \"config\": {}}}',
  NULL,
  NULL,
  4,
  NULL,
  NULL,
  NULL,
  NULL
);


-- PowerMem记忆配置说明
UPDATE `ai_model_config` SET
`doc_link` = 'https://github.com/oceanbase/powermem',
`remark` = 'PowerMem是OceanBase开源的agent记忆组件，通过本地LLM进行记忆总结
GitHub: https://github.com/oceanbase/powermem
官网: https://www.powermem.ai/
使用示例: https://github.com/oceanbase/powermem/tree/main/examples

【费用说明】
PowerMem本身免费，实际费用取决于所选LLM和数据库：
- 使用sqlite + 免费LLM(如glm-4-flash) = 完全免费
- 使用云端LLM或云端数据库 = 按对应服务收费

【enable_user_profile】用户画像功能
- false: 使用普通记忆模式(AsyncMemory)
- true: 使用用户画像模式(UserMemory)，自动提取用户信息
- 用户画像功能支持: oceanbase、seekdb、sqlite (powermem 0.3.0+)

【llm】LLM配置 - 用于记忆总结和用户画像提取
  provider: LLM提供商，可选值：
    - qwen: 通义千问 (https://bailian.console.aliyun.com/?apiKey=1#/api-key)
    - openai: OpenAI兼容接口
    - zhipu: 智谱AI (https://bigmodel.cn/usercenter/proj-mgmt/apikeys) - 推荐使用免费的glm-4-flash
  config: LLM配置参数
    - api_key: API密钥 (必填)
    - model: 模型名称，如 qwen-plus、glm-4-flash 等
    - openai_base_url: 自定义服务地址 (可选)，如 https://api.openai.com/v1
  示例：
    {"provider": "zhipu", "config": {"api_key": "your_key", "model": "glm-4-flash"}}
    {"provider": "qwen", "config": {"api_key": "your_key", "model": "qwen-plus"}}

【embedder】Embedding配置 - 用于向量化记忆内容
  provider: 嵌入模型提供商，可选值：
    - qwen: 通义千问
    - openai: OpenAI兼容接口
  config: Embedding配置参数
    - api_key: API密钥 (必填)
    - model: 模型名称，如 text-embedding-v4、text-embedding-3-small 等
    - openai_base_url: 自定义服务地址 (可选)
    - embedding_dims: 向量维度 (可选)，非1536时需配置
  示例：
    {"provider": "openai", "config": {"api_key": "your_key", "model": "text-embedding-v4", "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"}}

【vector_store】数据库存储配置 - 用于存储向量化的记忆
  provider: 数据库类型，可选值：
    - sqlite: 轻量级本地数据库 (推荐入门使用，无需额外配置)
    - oceanbase: OceanBase数据库 (推荐生产使用，最佳性能)
    - seekdb: SeekDB (推荐，AI应用存储一体)
    - postgres: PostgreSQL数据库

  SQLite配置 (无需额外配置):
    {"provider": "sqlite", "config": {}}

  OceanBase配置示例:
    {"provider": "oceanbase", "config": {
      "host": "127.0.0.1",
      "port": 2881,
      "user": "root@test",
      "password": "your_password",
      "db_name": "powermem",
      "collection_name": "memories",
      "embedding_model_dims": 1024
    }}
  注意：
    - collection_name: 默认表名，如创建维度错误请删除此表或更改名称
    - embedding_model_dims: 嵌入向量维度，需与embedder的模型维度匹配
      例如智谱：embedding-2维度是1024，embedding-3维度是2048

【推荐配置组合】
1. 完全免费方案：
   - LLM: zhipu + glm-4-flash (免费)
   - Embedder: 通义千问 text-embedding-v4
   - Database: sqlite

2. 生产环境方案：
   - LLM: qwen-plus 或其他商业模型
   - Embedder: text-embedding-v4
   - Database: oceanbase 或 seekdb
'
WHERE `id` = 'Memory_powermem';
