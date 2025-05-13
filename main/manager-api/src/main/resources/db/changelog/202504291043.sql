-- 增加FunASR服务语音识别模型供应器和配置
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_ASR_FunASRServer';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_FunASRServer', 'ASR', 'fun_server', 'FunASR服务语音识别', '[{"key":"host","label":"服务地址","type":"string"},{"key":"port","label":"端口号","type":"number"}]', 4, 1, NOW(), 1, NOW());

DELETE FROM `ai_model_config` WHERE `id` = 'ASR_FunASRServer';
INSERT INTO `ai_model_config` VALUES ('ASR_FunASRServer', 'ASR', 'FunASRServer', 'FunASR服务语音识别', 0, 1, '{\"type\": \"fun_server\", \"host\": \"127.0.0.1\", \"port\": 10096}', NULL, NULL, 5, NULL, NULL, NULL, NULL);

-- 修改ai_model_config表的remark字段类型为TEXT
ALTER TABLE `ai_model_config` MODIFY COLUMN `remark` TEXT COMMENT '备注'; 

-- 更新ASR模型配置的说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md',
`remark` = '独立部署FunASR，使用FunASR的API服务，只需要五句话
第一句：mkdir -p ./funasr-runtime-resources/models
第二句：sudo docker run -d -p 10096:10095 --privileged=true -v $PWD/funasr-runtime-resources/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
上一句话执行后会进入到容器，继续第三句：cd FunASR/runtime
不要退出容器，继续在容器中执行第四句：nohup bash run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx  --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx  --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &
上一句话执行后会进入到容器，继续第五句：tail -f log.txt
第五句话执行完后，会看到模型下载日志，下载完后就可以连接使用了
以上是使用CPU推理，如果有GPU，详细参考：https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md' WHERE `id` = 'ASR_FunASRServer';

-- 更新FunASR本地模型配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/modelscope/FunASR',
`remark` = 'FunASR本地模型配置说明：
1. 需要下载模型文件到xiaozhi-server/models/SenseVoiceSmall目录
2. 支持中日韩粤语音识别
3. 本地推理，无需网络连接
4. 待识别文件保存在tmp/目录' WHERE `id` = 'ASR_FunASR';

-- 更新SherpaASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/k2-fsa/sherpa-onnx',
`remark` = 'SherpaASR配置说明：
1. 运行时自动下载模型文件到models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17目录
2. 支持中文、英文、日语、韩语、粤语等多种语言
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录' WHERE `id` = 'ASR_SherpaASR';

-- 更新豆包ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 需要在火山引擎控制台创建应用并获取appid和access_token
2. 支持中文语音识别
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中' WHERE `id` = 'ASR_DoubaoASR';

-- 更新腾讯ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.cloud.tencent.com/cam/capi',
`remark` = '腾讯ASR配置说明：
1. 需要在腾讯云控制台创建应用并获取appid、secret_id和secret_key
2. 支持中文语音识别
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.cloud.tencent.com/cam/capi 获取密钥
2. 访问 https://console.cloud.tencent.com/asr/resourcebundle 领取免费资源
3. 获取appid、secret_id和secret_key
4. 填入配置文件中' WHERE `id` = 'ASR_TencentASR';

-- 更新TTS模型配置说明
-- EdgeTTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/rany2/edge-tts',
`remark` = 'EdgeTTS配置说明：
1. 使用微软Edge TTS服务
2. 支持多种语言和音色
3. 免费使用，无需注册
4. 需要网络连接
5. 输出文件保存在tmp/目录' WHERE `id` = 'TTS_EdgeTTS';

-- 豆包TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/8',
`remark` = '豆包TTS配置说明：
1. 访问 https://console.volcengine.com/speech/service/8
2. 需要在火山引擎控制台创建应用并获取appid和access_token
3. 山引擎语音一定要购买花钱，起步价30元，就有100并发了。如果用免费的只有2个并发，会经常报tts错误
4. 购买服务后，购买免费的音色后，可能要等半小时左右，才能使用。
5. 填入配置文件中' WHERE `id` = 'TTS_DoubaoTTS';

-- 硅基流动TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://cloud.siliconflow.cn/account/ak',
`remark` = '硅基流动TTS配置说明：
1. 访问 https://cloud.siliconflow.cn/account/ak
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'TTS_CosyVoiceSiliconflow';

-- Coze中文TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://www.coze.cn/open/oauth/pats',
`remark` = 'Coze中文TTS配置说明：
1. 访问 https://www.coze.cn/open/oauth/pats
2. 获取个人令牌
3. 填入配置文件中' WHERE `id` = 'TTS_CozeCnTTS';

-- FishSpeech配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/fishaudio/fish-speech',
`remark` = 'FishSpeech配置说明：
1. 需要本地部署FishSpeech服务
2. 支持自定义音色
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录
5. 运行服务示例命令：python -m tools.api_server --listen 0.0.0.0:8080 --llama-checkpoint-path "checkpoints/fish-speech-1.5" --decoder-checkpoint-path "checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth" --decoder-config-name firefly_gan_vq --compile' WHERE `id` = 'TTS_FishSpeech';

-- GPT-SoVITS V2配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/RVC-Boss/GPT-SoVITS',
`remark` = 'GPT-SoVITS V2配置说明：
1. 需要本地部署GPT-SoVITS服务
2. 支持自定义音色克隆
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录
部署步骤：
1. 运行服务示例命令：python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/demo.yaml' WHERE `id` = 'TTS_GPT_SOVITS_V2';

-- GPT-SoVITS V3配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/RVC-Boss/GPT-SoVITS',
`remark` = 'GPT-SoVITS V3配置说明：
1. 需要本地部署GPT-SoVITS V3服务
2. 支持自定义音色克隆
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录' WHERE `id` = 'TTS_GPT_SOVITS_V3';

-- MiniMax TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.minimaxi.com/',
`remark` = 'MiniMax TTS配置说明：
1. 需要在MiniMax平台创建账户并充值
2. 支持多种音色，当前配置使用female-shaonv
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://platform.minimaxi.com/ 注册账号
2. 访问 https://platform.minimaxi.com/user-center/payment/balance 充值
3. 访问 https://platform.minimaxi.com/user-center/basic-information 获取group_id
4. 访问 https://platform.minimaxi.com/user-center/basic-information/interface-key 获取api_key
5. 填入配置文件中' WHERE `id` = 'TTS_MinimaxTTS';

-- 阿里云TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云TTS配置说明：
1. 需要在阿里云平台开通智能语音交互服务
2. 支持多种音色，当前配置使用xiaoyun
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://nls-portal.console.aliyun.com/ 开通服务
2. 访问 https://nls-portal.console.aliyun.com/applist 获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取token
4. 填入配置文件中
注意：token是临时的24小时有效，长期使用需要配置access_key_id和access_key_secret' WHERE `id` = 'TTS_AliyunTTS';

-- 腾讯TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.cloud.tencent.com/cam/capi',
`remark` = '腾讯TTS配置说明：
1. 需要在腾讯云平台开通智能语音交互服务
2. 支持多种音色，当前配置使用101001
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.cloud.tencent.com/cam/capi 获取密钥
2. 访问 https://console.cloud.tencent.com/tts/resourcebundle 领取免费资源
3. 创建新应用
4. 获取appid、secret_id和secret_key
5. 填入配置文件中' WHERE `id` = 'TTS_TencentTTS';

-- 302AI TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://dash.302.ai/',
`remark` = '302AI TTS配置说明：
1. 需要在302平台创建账户并获取API密钥
2. 支持多种音色，当前配置使用湾湾小何音色
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://dash.302.ai/ 注册账号
2. 访问 https://dash.302.ai/apis/list 获取API密钥
3. 填入配置文件中
价格：$35/百万字符' WHERE `id` = 'TTS_TTS302AI';

-- 机智云TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://agentrouter.gizwitsapi.com/panel/token',
`remark` = '机智云TTS配置说明：
1. 需要在机智云平台获取API密钥
2. 支持多种音色，当前配置使用湾湾小何音色
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://agentrouter.gizwitsapi.com/panel/token 获取API密钥
2. 填入配置文件中
注意：前一万名注册的用户，将送5元体验金额' WHERE `id` = 'TTS_GizwitsTTS';

-- ACGN TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://acgn.ttson.cn/',
`remark` = 'ACGN TTS配置说明：
1. 需要在ttson平台购买token
2. 支持多种角色音色，当前配置使用角色ID：1695
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://acgn.ttson.cn/ 查看角色列表
2. 访问 www.ttson.cn 购买token
3. 填入配置文件中
开发相关疑问请提交至网站上的qq' WHERE `id` = 'TTS_ACGNTTS';

-- OpenAI TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.openai.com/api-keys',
`remark` = 'OpenAI TTS配置说明：
1. 需要在OpenAI平台获取API密钥
2. 支持多种音色，当前配置使用onyx
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://platform.openai.com/api-keys 获取API密钥
2. 填入配置文件中
注意：国内需要使用代理访问' WHERE `id` = 'TTS_OpenAITTS';

-- 自定义TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '自定义TTS配置说明：
1. 支持自定义TTS接口服务
2. 使用GET方式请求
3. 需要网络连接
4. 输出文件保存在tmp/目录
配置说明：
1. 在params中配置请求参数
2. 在headers中配置请求头
3. 设置返回音频格式' WHERE `id` = 'TTS_CustomTTS';

-- 火山引擎边缘大模型网关TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关TTS配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥，搜索并勾选 Doubao-语音合成
3. 如果需要使用LLM，一并勾选 Doubao-pro-32k-functioncall
4. 访问 https://console.volcengine.com/vei/aigateway/tokens-list 获取密钥
5. 填入配置文件中
音色列表参考：https://www.volcengine.com/docs/6561/1257544' WHERE `id` = 'TTS_VolcesAiGatewayTTS';

-- 更新LLM模型配置说明
-- ChatGLM配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bigmodel.cn/usercenter/proj-mgmt/apikeys',
`remark` = 'ChatGLM配置说明：
1. 访问 https://bigmodel.cn/usercenter/proj-mgmt/apikeys
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'LLM_ChatGLMLLM';

-- Ollama配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://ollama.com/',
`remark` = 'Ollama配置说明：
1. 安装Ollama服务
2. 运行命令：ollama pull qwen2.5
3. 确保服务运行在http://localhost:11434' WHERE `id` = 'LLM_OllamaLLM';

-- 通义千问配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1#/api-key',
`remark` = '通义千问配置说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key
2. 获取API密钥
3. 填入配置文件中，当前配置使用qwen-turbo模型
4. 支持自定义参数：temperature=0.7, max_tokens=500, top_p=1, top_k=50' WHERE `id` = 'LLM_AliLLM';

-- 通义百炼配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1#/api-key',
`remark` = '通义百炼配置说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key
2. 获取app_id和api_key
3. 填入配置文件中' WHERE `id` = 'LLM_AliAppLLM';

-- 豆包大模型配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement',
`remark` = '豆包大模型配置说明：
1. 访问 https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement
2. 开通Doubao-1.5-pro服务
3. 访问 https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey 获取API密钥
4. 填入配置文件中
5. 当前建议使用doubao-1-5-pro-32k-250115
注意：有免费额度500000token' WHERE `id` = 'LLM_DoubaoLLM';

-- DeepSeek配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.deepseek.com/',
`remark` = 'DeepSeek配置说明：
1. 访问 https://platform.deepseek.com/
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'LLM_DeepSeekLLM';

-- Dify配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://cloud.dify.ai/',
`remark` = 'Dify配置说明：
1. 访问 https://cloud.dify.ai/
2. 注册并获取API密钥
3. 填入配置文件中
4. 支持多种对话模式：workflows/run, chat-messages, completion-messages
5. 平台设置的角色定义会失效，需要在Dify控制台设置
注意：建议使用本地部署的Dify接口，国内部分区域访问公有云接口可能受限' WHERE `id` = 'LLM_DifyLLM';

-- Gemini配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://aistudio.google.com/apikey',
`remark` = 'Gemini配置说明：
1. 使用谷歌Gemini API服务
2. 当前配置使用gemini-2.0-flash模型
3. 需要网络连接
4. 支持配置代理
申请步骤：
1. 访问 https://aistudio.google.com/apikey
2. 创建API密钥
3. 填入配置文件中
注意：若在中国境内使用，请遵守《生成式人工智能服务管理暂行办法》' WHERE `id` = 'LLM_GeminiLLM';

-- Coze配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://www.coze.cn/open/oauth/pats',
`remark` = 'Coze配置说明：
1. 使用Coze平台服务
2. 需要bot_id、user_id和个人令牌
3. 需要网络连接
申请步骤：
1. 访问 https://www.coze.cn/open/oauth/pats
2. 获取个人令牌
3. 手动计算bot_id和user_id
4. 填入配置文件中' WHERE `id` = 'LLM_CozeLLM';

-- LM Studio配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://lmstudio.ai/',
`remark` = 'LM Studio配置说明：
1. 使用本地部署的LM Studio服务
2. 当前配置使用deepseek-r1-distill-llama-8b@q4_k_m模型
3. 本地推理，无需网络连接
4. 需要预先下载模型
部署步骤：
1. 安装LM Studio
2. 从社区下载模型
3. 确保服务运行在http://localhost:1234/v1' WHERE `id` = 'LLM_LMStudioLLM';

-- FastGPT配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://cloud.tryfastgpt.ai/account/apikey',
`remark` = 'FastGPT配置说明：
1. 使用FastGPT平台服务
2. 需要网络连接
3. 配置文件中的prompt无效，需要在FastGPT控制台设置
4. 支持自定义变量
申请步骤：
1. 访问 https://cloud.tryfastgpt.ai/account/apikey
2. 获取API密钥
3. 填入配置文件中' WHERE `id` = 'LLM_FastgptLLM';

-- Xinference配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/xorbitsai/inference',
`remark` = 'Xinference配置说明：
1. 使用本地部署的Xinference服务
2. 当前配置使用qwen2.5:72b-AWQ模型
3. 本地推理，无需网络连接
4. 需要预先启动对应模型
部署步骤：
1. 安装Xinference
2. 启动服务并加载模型
3. 确保服务运行在http://localhost:9997' WHERE `id` = 'LLM_XinferenceLLM';

-- Xinference小模型配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/xorbitsai/inference',
`remark` = 'Xinference小模型配置说明：
1. 使用本地部署的Xinference服务
2. 当前配置使用qwen2.5:3b-AWQ模型
3. 本地推理，无需网络连接
4. 用于意图识别
部署步骤：
1. 安装Xinference
2. 启动服务并加载模型
3. 确保服务运行在http://localhost:9997' WHERE `id` = 'LLM_XinferenceSmallLLM';

-- 火山引擎边缘大模型网关LLM配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关LLM配置说明：
1. 使用火山引擎边缘大模型网关服务
2. 需要网关访问密钥
3. 需要网络连接
4. 支持function_call功能
申请步骤：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥，搜索并勾选 Doubao-pro-32k-functioncall
3. 如果需要使用语音合成，一并勾选 Doubao-语音合成
4. 访问 https://console.volcengine.com/vei/aigateway/tokens-list 获取密钥
5. 填入配置文件中' WHERE `id` = 'LLM_VolcesAiGatewayLLM';

-- 更新Memory模型配置说明
-- 无记忆配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '无记忆配置说明：
1. 不保存对话历史
2. 每次对话都是独立的
3. 无需额外配置
4. 适合对隐私要求高的场景' WHERE `id` = 'Memory_nomem';

-- 本地短期记忆配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '本地短期记忆配置说明：
1. 使用本地存储保存对话历史
2. 通过selected_module的llm总结对话内容
3. 数据保存在本地，不会上传到服务器
4. 适合注重隐私的场景
5. 无需额外配置' WHERE `id` = 'Memory_mem_local_short';

-- Mem0AI记忆配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://app.mem0.ai/dashboard/api-keys',
`remark` = 'Mem0AI记忆配置说明：
1. 使用Mem0AI服务保存对话历史
2. 需要API密钥
3. 需要网络连接
4. 每月有1000次免费调用
申请步骤：
1. 访问 https://app.mem0.ai/dashboard/api-keys
2. 获取API密钥
3. 填入配置文件中' WHERE `id` = 'Memory_mem0ai';

-- 更新Intent模型配置说明
-- 无意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '无意图识别配置说明：
1. 不进行意图识别
2. 所有对话直接传递给LLM处理
3. 无需额外配置
4. 适合简单对话场景' WHERE `id` = 'Intent_nointent';

-- LLM意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = 'LLM意图识别配置说明：
1. 使用独立的LLM进行意图识别
2. 默认使用selected_module.LLM的模型
3. 可以配置使用独立的LLM（如免费的ChatGLMLLM）
4. 通用性强，但会增加处理时间
5. 不支持控制音量大小等iot操作
配置说明：
1. 在llm字段中指定使用的LLM模型
2. 如果不指定，则使用selected_module.LLM的模型' WHERE `id` = 'Intent_intent_llm';

-- 函数调用意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '函数调用意图识别配置说明：
1. 使用LLM的function_call功能进行意图识别
2. 需要所选择的LLM支持function_call
3. 按需调用工具，处理速度快
4. 支持所有iot指令
5. 默认已加载以下功能：
   - handle_exit_intent（退出识别）
   - play_music（音乐播放）
   - change_role（角色切换）
   - get_weather（天气查询）
   - get_news（新闻查询）
配置说明：
1. 在functions字段中配置需要加载的功能模块
2. 系统默认已加载基础功能，无需重复配置
3. 可以添加自定义功能模块' WHERE `id` = 'Intent_function_call';

-- 更新VAD模型配置说明
-- SileroVAD配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/snakers4/silero-vad',
`remark` = 'SileroVAD配置说明：
1. 使用SileroVAD模型进行语音活动检测
2. 本地推理，无需网络连接
3. 需要下载模型文件到models/snakers4_silero-vad目录
4. 可配置参数：
   - threshold: 0.5（语音检测阈值）
   - min_silence_duration_ms: 700（最小静音持续时间，单位毫秒）
5. 如果说话停顿比较长，可以适当增加min_silence_duration_ms的值' WHERE `id` = 'VAD_SileroVAD';
