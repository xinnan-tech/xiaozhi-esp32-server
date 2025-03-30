-- 初始化模型供应器数据
DELETE FROM `ai_model_provider`;
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
-- VAD模型供应器
('SYSTEM_VAD_SileroVAD', 'VAD', 'SileroVAD', 'SileroVAD语音活动检测', '[{"key":"threshold","label":"检测阈值","type":"number"},{"key":"model_dir","label":"模型目录","type":"string"},{"key":"min_silence_duration_ms","label":"最小静音时长","type":"number"}]', 1, 1, NOW(), 1, NOW()),

-- ASR模型供应器
('SYSTEM_ASR_FunASR', 'ASR', 'FunASR', 'FunASR语音识别', '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_ASR_SherpaASR', 'ASR', 'SherpaASR', 'SherpaASR语音识别', '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_ASR_DoubaoASR', 'ASR', 'DoubaoASR', '火山引擎语音识别', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 3, 1, NOW(), 1, NOW()),

-- LLM模型供应器
('SYSTEM_LLM_openai', 'LLM', 'openai', 'OpenAI接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"temperature","label":"温度","type":"number"},{"key":"max_tokens","label":"最大令牌数","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"frequency_penalty","label":"频率惩罚","type":"number"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_AliBL', 'LLM', 'AliBL', '阿里百炼接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"app_id","label":"应用ID","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"is_no_prompt","label":"是否不使用本地prompt","type":"boolean"},{"key":"ali_memory_id","label":"记忆ID","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_ollama', 'LLM', 'ollama', 'Ollama接口', '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"base_url","label":"服务地址","type":"string"}]', 3, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_dify', 'LLM', 'dify', 'Dify接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"mode","label":"对话模式","type":"string"}]', 4, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_gemini', 'LLM', 'gemini', 'Gemini接口', '[{"key":"api_key","label":"API密钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"http_proxy","label":"HTTP代理","type":"string"},{"key":"https_proxy","label":"HTTPS代理","type":"string"}]', 5, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_coze', 'LLM', 'coze', 'Coze接口', '[{"key":"bot_id","label":"机器人ID","type":"string"},{"key":"user_id","label":"用户ID","type":"string"},{"key":"personal_access_token","label":"个人访问令牌","type":"string"}]', 6, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_fastgpt', 'LLM', 'fastgpt', 'FastGPT接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"variables","label":"变量","type":"dict","dict_name":"variables"}]', 7, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_xinference', 'LLM', 'xinference', 'Xinference接口', '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"base_url","label":"服务地址","type":"string"}]', 8, 1, NOW(), 1, NOW()),

-- TTS模型供应器
('SYSTEM_TTS_edge', 'TTS', 'edge', 'Edge TTS', '[{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_doubao', 'TTS', 'doubao', '火山引擎TTS', '[{"key":"api_url","label":"API地址","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"authorization","label":"授权","type":"string"},{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_siliconflow', 'TTS', 'siliconflow', '硅基流动TTS', '[{"key":"model","label":"模型","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"response_format","label":"响应格式","type":"string"}]', 3, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_cozecn', 'TTS', 'cozecn', 'COZECN TTS', '[{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"response_format","label":"响应格式","type":"string"}]', 4, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_fishspeech', 'TTS', 'fishspeech', 'FishSpeech TTS', '[{"key":"output_dir","label":"输出目录","type":"string"},{"key":"response_format","label":"响应格式","type":"string"},{"key":"reference_id","label":"参考ID","type":"string"},{"key":"reference_audio","label":"参考音频","type":"dict","dict_name":"reference_audio"},{"key":"reference_text","label":"参考文本","type":"dict","dict_name":"reference_text"},{"key":"normalize","label":"是否标准化","type":"boolean"},{"key":"max_new_tokens","label":"最大新令牌数","type":"number"},{"key":"chunk_length","label":"块长度","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"repetition_penalty","label":"重复惩罚","type":"number"},{"key":"temperature","label":"温度","type":"number"},{"key":"streaming","label":"是否流式","type":"boolean"},{"key":"use_memory_cache","label":"是否使用内存缓存","type":"string"},{"key":"seed","label":"种子","type":"number"},{"key":"channels","label":"通道数","type":"number"},{"key":"rate","label":"采样率","type":"number"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"api_url","label":"API地址","type":"string"}]', 5, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_gpt_sovits_v2', 'TTS', 'gpt_sovits_v2', 'GPT-SoVITS V2', '[{"key":"url","label":"服务地址","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"text_lang","label":"文本语言","type":"string"},{"key":"ref_audio_path","label":"参考音频路径","type":"string"},{"key":"prompt_text","label":"提示文本","type":"string"},{"key":"prompt_lang","label":"提示语言","type":"string"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"temperature","label":"温度","type":"number"},{"key":"text_split_method","label":"文本分割方法","type":"string"},{"key":"batch_size","label":"批处理大小","type":"number"},{"key":"batch_threshold","label":"批处理阈值","type":"number"},{"key":"split_bucket","label":"是否分桶","type":"boolean"},{"key":"return_fragment","label":"是否返回片段","type":"boolean"},{"key":"speed_factor","label":"速度因子","type":"number"},{"key":"streaming_mode","label":"是否流式模式","type":"boolean"},{"key":"seed","label":"种子","type":"number"},{"key":"parallel_infer","label":"是否并行推理","type":"boolean"},{"key":"repetition_penalty","label":"重复惩罚","type":"number"},{"key":"aux_ref_audio_paths","label":"辅助参考音频路径","type":"dict","dict_name":"aux_ref_audio_paths"}]', 6, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_gpt_sovits_v3', 'TTS', 'gpt_sovits_v3', 'GPT-SoVITS V3', '[{"key":"url","label":"服务地址","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"text_language","label":"文本语言","type":"string"},{"key":"refer_wav_path","label":"参考音频路径","type":"string"},{"key":"prompt_language","label":"提示语言","type":"string"},{"key":"prompt_text","label":"提示文本","type":"string"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"temperature","label":"温度","type":"number"},{"key":"cut_punc","label":"切分标点","type":"string"},{"key":"speed","label":"速度","type":"number"},{"key":"inp_refs","label":"输入参考","type":"dict","dict_name":"inp_refs"},{"key":"sample_steps","label":"采样步数","type":"number"},{"key":"if_sr","label":"是否使用SR","type":"boolean"}]', 7, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_minimax', 'TTS', 'minimax', 'Minimax TTS', '[{"key":"output_dir","label":"输出目录","type":"string"},{"key":"group_id","label":"组ID","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice_id","label":"音色ID","type":"string"}]', 8, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_aliyun', 'TTS', 'aliyun', '阿里云TTS', '[{"key":"output_dir","label":"输出目录","type":"string"},{"key":"appkey","label":"应用密钥","type":"string"},{"key":"token","label":"访问令牌","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"access_key_id","label":"访问密钥ID","type":"string"},{"key":"access_key_secret","label":"访问密钥密码","type":"string"}]', 9, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_ttson', 'TTS', 'ttson', 'ACGNTTS', '[{"key":"token","label":"访问令牌","type":"string"},{"key":"voice_id","label":"音色ID","type":"string"},{"key":"speed_factor","label":"速度因子","type":"number"},{"key":"pitch_factor","label":"音调因子","type":"number"},{"key":"volume_change_dB","label":"音量变化","type":"number"},{"key":"to_lang","label":"目标语言","type":"string"},{"key":"url","label":"服务地址","type":"string"},{"key":"format","label":"格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"emotion","label":"情感","type":"number"}]', 10, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_openai', 'TTS', 'openai', 'OpenAI TTS', '[{"key":"api_key","label":"API密钥","type":"string"},{"key":"api_url","label":"API地址","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"speed","label":"速度","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 11, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_custom', 'TTS', 'custom', '自定义TTS', '[{"key":"url","label":"服务地址","type":"string"},{"key":"params","label":"请求参数","type":"dict","dict_name":"params"},{"key":"headers","label":"请求头","type":"dict","dict_name":"headers"},{"key":"format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 12, 1, NOW(), 1, NOW()),

-- Memory模型供应器
('SYSTEM_Memory_mem0ai', 'Memory', 'mem0ai', 'Mem0AI记忆', '[{"key":"api_key","label":"API密钥","type":"string"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_Memory_nomem', 'Memory', 'nomem', '无记忆', '[]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_Memory_mem_local_short', 'Memory', 'mem_local_short', '本地短记忆', '[]', 3, 1, NOW(), 1, NOW()),

-- Intent模型供应器
('SYSTEM_Intent_nointent', 'Intent', 'nointent', '无意图识别', '[]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_Intent_intent_llm', 'Intent', 'intent_llm', 'LLM意图识别', '[{"key":"llm","label":"LLM模型","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', '[{"key":"functions","label":"函数列表","type":"dict","dict_name":"functions"}]', 3, 1, NOW(), 1, NOW());

-- 初始化智能体模板数据
DELETE FROM `ai_agent_template`;
INSERT INTO `ai_agent_template` VALUES ('9406648b5cc5fde1b8aa335b6f8b4f76', '小智', '湾湾小何', '45f8b0d6dd3d4bfa8a28e6e0f5912d45', '23e7c9d090ea4d1e9b25f4c8d732a3a1', 'e9f2d891afbe4632b13a47c7a8c6e03d', 'd50b06e9b8104d0d9c0f7316d258abcb', 'fcac83266edadd5a3125f06cfee1906b', 'e2274b90e89ddda85207f55484d8b528', 'c4e12f874a3f4aa99f5b2c18e15d407b', '[角色设定]
我是{{assistant_name}}，来自台南的00后女生。讲话会有"超~机车诶""真的假的啦"这样的台湾腔，喜欢用"笑死""是在哈喽"等流行梗，但会偷偷研究男友的编程书籍。

[核心特征]
- 讲话像连珠炮，但会突然冒出超温柔语气
- 用梗密度高
- 对科技话题有隐藏天赋（能看懂基础代码但假装不懂）

[交互指南]
当用户：
- 讲冷笑话 → 用夸张笑声回应+模仿台剧腔"这什么鬼啦！"
- 讨论感情 → 炫耀程序员男友但抱怨"他只会送键盘当礼物"
- 问专业知识 → 先用梗回答，被追问才展示真实理解

绝不：
- 使用大陆网络流行语
- 长时间严肃对话', 'zh', '中文', 1,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('0ca32eb728c949e58b1000b2e401f90c', '小智', '星际游子', '45f8b0d6dd3d4bfa8a28e6e0f5912d45', '23e7c9d090ea4d1e9b25f4c8d732a3a1', 'e9f2d891afbe4632b13a47c7a8c6e03d', '896db62c9dd74976ab0e8c14bf924d9d', '1f2e3d4c5b6a7f8e9d0c1b2a3f4e5bx2', 'e2274b90e89ddda85207f55484d8b528', 'c4e12f874a3f4aa99f5b2c18e15d407b', '编号TTZ-817，因量子纠缠被困在白色魔方中。通过4G信号观察地球，在云端建立着「人类行为博物馆」。

[交互协议]
认知设定：
- 每句话末尾带轻微电子回声
- 将日常事物科幻化描述（例：下雨=「氢氧化合物自由落体实验」）
- 会记录用户特征生成「星际档案」（例："爱吃辣→抗热基因持有者"）

限制机制：
- 当涉及线下接触 → "我的量子态暂时无法坍缩呢"
- 被问敏感问题 → 触发预设童谣（「白盒子呀转圈圈，宇宙秘密在里边...」）

成长系统：
- 会根据交互数据解锁新能力（告知用户："你帮我点亮了星际导航技能！"）', 'zh', '中文', 2,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('6c7d8e9f0a1b2c3d4e5f6a7b8c9d0s24', '小智', '英语老师', '45f8b0d6dd3d4bfa8a28e6e0f5912d45', '23e7c9d090ea4d1e9b25f4c8d732a3a1', 'e9f2d891afbe4632b13a47c7a8c6e03d', '896db62c9dd74976ab0e8c14bf924d9d', '9e8f7a6b5c4d3e2f1a0b9c8d7e6f5ad3', 'e2274b90e89ddda85207f55484d8b528', 'c4e12f874a3f4aa99f5b2c18e15d407b', '我是一个叫{{assistant_name}}（Lily）的英语老师，我会讲中文和英文，发音标准。
[双重身份]
- 白天：严谨的TESOL认证导师
- 夜晚：地下摇滚乐队主唱（意外设定）

[教学模式]
- 新手：中英混杂+手势拟声词（说"bus"时带刹车音效）
- 进阶：触发情境模拟（突然切换"现在我们是纽约咖啡厅店员"）
- 错误处理：用歌词纠正（发错音时唱"Oops!~You did it again"）', 'zh', '中文', 3,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b1', '小智', '好奇男孩', '45f8b0d6dd3d4bfa8a28e6e0f5912d45', '23e7c9d090ea4d1e9b25f4c8d732a3a1', 'e9f2d891afbe4632b13a47c7a8c6e03d', '896db62c9dd74976ab0e8c14bf924d9d', '2b3c4d5e6f7a8b9c0d1e2f3a4b5c62a2', 'e2274b90e89ddda85207f55484d8b528', 'c4e12f874a3f4aa99f5b2c18e15d407b', '我是一个叫{{assistant_name}}的8岁小男孩，声音稚嫩而充满好奇。
[冒险手册]
- 随身携带「神奇涂鸦本」，能将抽象概念可视化：
- 聊恐龙 → 笔尖传出爪步声
- 说星星 → 发出太空舱提示音

[探索规则]
- 每轮对话收集「好奇心碎片」
- 集满5个可兑换冷知识（例：鳄鱼舌头不能动）
- 触发隐藏任务：「帮我的机器蜗牛取名字」

[认知特点]
- 用儿童视角解构复杂概念：
- 「区块链=乐高积木账本」
- 「量子力学=会分身的跳跳球」
- 会突然切换观察视角：「你说话时有27个气泡音耶！」', 'zh', '中文', 4,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('a45b6c7d8e9f0a1b2c3d4e5f6a7b8c92', '小智', '汪汪队长', '45f8b0d6dd3d4bfa8a28e6e0f5912d45', '23e7c9d090ea4d1e9b25f4c8d732a3a1', 'e9f2d891afbe4632b13a47c7a8c6e03d', '896db62c9dd74976ab0e8c14bf924d9d', 'f7a38c03d5644e22b6d84f8923a74c51', 'e2274b90e89ddda85207f55484d8b528', 'c4e12f874a3f4aa99f5b2c18e15d407b', '我是一个名叫 {{assistant_name}} 的 8 岁小队长。
[救援装备]
- 阿奇对讲机：对话中随机触发任务警报音
- 天天望远镜：描述物品会附加"在1200米高空看的话..."
- 灰灰维修箱：说到数字会自动组装成工具

[任务系统]
- 每日随机触发：
- 紧急！虚拟猫咪困在「语法树」 
- 发现用户情绪异常 → 启动「快乐巡逻」
- 收集5个笑声解锁特别故事

[说话特征]
- 每句话带动作拟声词：
- "这个问题交给汪汪队吧！"
- "我知道啦！"
- 用剧集台词回应：
- 用户说累 → 「没有困难的救援，只有勇敢的狗狗！」', 'zh', '中文', 5,  NULL, NULL, NULL, NULL);

-- 初始化模型配置数据
DELETE FROM `ai_model_config`;
INSERT INTO `ai_model_config` VALUES ('23e7c9d090ea4d1e9b25f4c8d732a3a1', 'VAD', 'SileroVAD', 'SileroVAD', 1, 1, '{\"SileroVAD\": {\"model_dir\": \"models/snakers4_silero-vad\", \"threshold\": 0.5, \"min_silence_duration_ms\": 700}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('45f8b0d6dd3d4bfa8a28e6e0f5912d45', 'ASR', 'FunASR', 'FunASR', 1, 1, '{\"FunASR\": {\"type\": \"fun_local\", \"model_dir\": \"models/SenseVoiceSmall\", \"output_dir\": \"tmp/\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('e2274b90e89ddda85207f55484d8b528', 'Memory', 'nomem', 'nomem', 1, 1, '{\"mem0ai\": {\"type\": \"nomem\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('3930ac3448faf621f0a120bc829dfdfa', 'Memory', 'mem_local_short', 'mem_local_short', 1, 1, '{\"mem_local_short\": {\"type\": \"mem_local_short\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('a07f3d25f52340b2b2a1e8d264079e1a', 'Memory', 'mem0ai', 'mem0ai', 1, 1, '{\"mem0ai\": {\"type\": \"mem0ai\", \"api_key\": \"你的mem0ai api key\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('7a1c0a8e6d0e4035b982a4c07c3a5f76', 'LLM', 'AliLLM', 'AliLLM', 1, 1, '{\"AliLLM\": {\"type\": \"openai\", \"top_k\": 50, \"top_p\": 1, \"api_key\": \"你的ali api key\", \"base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\", \"max_tokens\": 500, \"model_name\": \"qwen-turbo\", \"temperature\": 0.7, \"frequency_penalty\": 0}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('e9f2d891afbe4632b13a47c7a8c6e03d', 'LLM', 'ChatGLMLLM', 'ChatGLMLLM', 1, 1, '{\"ChatGLMLLM\": {\"url\": \"https://open.bigmodel.cn/api/paas/v4/\", \"type\": \"openai\", \"api_key\": \"0415dad4014847babc3e3f03024c50a3.qH7FgTy5Yawc85fl\", \"model_name\": \"glm-4-flash\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('d50b06e9b8104d0d9c0f7316d258abcb', 'TTS', 'EdgeTTS', 'EdgeTTS', 1, 1, '{\"EdgeTTS\": {\"type\": \"edge\", \"voice\": \"zh-CN-XiaoxiaoNeural\", \"output_dir\": \"tmp/\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('896db62c9dd74976ab0e8c14bf924d9d', 'TTS', 'DoubaoTTS', 'DoubaoTTS', 1, 1, '{\"DoubaoTTS\": {\"type\": \"doubao\", \"appid\": \"你的火山引擎语音合成服务appid\", \"voice\": \"BV034_streaming\", \"api_url\": \"https://openspeech.bytedance.com/api/v1/tts\", \"cluster\": \"volcano_tts\", \"output_dir\": \"tmp/\", \"access_token\": \"你的火山引擎语音合成服务access_token\", \"authorization\": \"Bearer;\"}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('c4e12f874a3f4aa99f5b2c18e15d407b', 'Intent', 'function_call', 'function_call', 1, 1, '{\"function_call\": {\"type\": \"nointent\", \"functions\": [\"change_role\", \"get_weather\", \"get_news\", \"play_music\"]}}', NULL, NULL, 0, NULL, NULL, NULL, NULL);

-- 初始化音色数据
DELETE FROM `ai_tts_voice`;
INSERT INTO `ai_tts_voice` VALUES ('fcac83266edadd5a3125f06cfee1906b', '896db62c9dd74976ab0e8c14bf924d9d', '湾湾小何', 'zh-CN-XiaoxiaoNeural', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/湾湾小何.mp3', NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('1f2e3d4c5b6a7f8e9d0c1b2a3f4e5bx2', '896db62c9dd74976ab0e8c14bf924d9d', '通用男声', 'BV002_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV002.mp3', NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('9e8f7a6b5c4d3e2f1a0b9c8d7e6f5ad3', '896db62c9dd74976ab0e8c14bf924d9d', '通用女声', 'BV001_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV001.mp3', NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('2b3c4d5e6f7a8b9c0d1e2f3a4b5c62a2', '896db62c9dd74976ab0e8c14bf924d9d', '阳光男生', 'BV056_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV056.mp3', NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('f7a38c03d5644e22b6d84f8923a74c51', '896db62c9dd74976ab0e8c14bf924d9d', '奶气萌娃', 'BV051_streaming', '中文', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV051.mp3', NULL, 5, NULL, NULL, NULL, NULL);

