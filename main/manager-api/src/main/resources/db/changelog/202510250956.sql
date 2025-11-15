-- 添加RAG模型供应器和配置
-- -------------------------------------------------------

-- 添加RAG模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_RAG_ragflow';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_RAG_ragflow', 'RAG', 'ragflow', 'RAGFlow', '[{"key": "base_url", "type": "string", "label": "服务地址"}, {"key": "api_key", "type": "string", "label": "API密钥"}]', 1, 1, NOW(), 1, NOW());

-- 添加RAG模型配置
delete from `ai_model_config` where id = 'RAG_RAGFlow';
INSERT INTO `ai_model_config` VALUES ('RAG_RAGFlow', 'RAG', 'ragflow', 'RAGFlow', 1, 1, '{"type": "ragflow", "base_url": "http://localhost", "api_key": "你的RAG密钥"}', 'https://github.com/infiniflow/ragflow/blob/main/README_zh.md', 'RAGFlow配置说明：
一、快速部署教程（docker部署）
1.$ sysctl vm.max_map_count
2.$ sysctl -w vm.max_map_count=262144
3.$ git clone https://github.com/infiniflow/ragflow.git
4.docker compose -f docker-compose.yml up -d
5.$ docker logs -f docker-ragflow-cpu-1
6.注冊登录后，点击右上角头像，获得RAGFlow的API KEY和API服务器地址。使用RAGFlow前请在Model Provider中添加模型和设置默认模型。
二、如果您希望关掉注册功能
1.停止服务   docker compose down
2. sed -i ''s/REGISTER_ENABLED=1/REGISTER_ENABLED=0/g'' .env   
3.cat .env | grep -i register
4.看到REGISTER_ENABLED=0 重启服务即可。',  1, NULL, NULL, NULL, NULL);

