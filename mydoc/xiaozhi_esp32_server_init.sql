-- =============================================================
-- xiaozhi-esp32-server 数据库初始化脚本（合并版）
-- 生成日期: 2026-10-24
-- 来源: main/manager-api/src/main/resources/db/changelog/*.sql
-- 执行顺序: 按原项目脚本定义顺序（共 107 个脚本）
-- 适用: MySQL 8.x，空库 xiaozhi_esp32_server
-- 警告: 脚本开头会删除全部业务表，请勿在已有数据的库中执行
-- =============================================================

SET NAMES utf8mb4;

-- -------------------------------------------------------------
-- 清理旧结构
-- 说明：先统一删除所有表，避免库中残留旧表/旧字段导致后续
--       CREATE TABLE（如 ai_agent_context_provider）或 ALTER 报错中断
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `ai_agent`;
DROP TABLE IF EXISTS `ai_agent_chat_audio`;
DROP TABLE IF EXISTS `ai_agent_chat_history`;
DROP TABLE IF EXISTS `ai_agent_chat_message`;
DROP TABLE IF EXISTS `ai_agent_chat_title`;
DROP TABLE IF EXISTS `ai_agent_context_provider`;
DROP TABLE IF EXISTS `ai_agent_correct_word_file`;
DROP TABLE IF EXISTS `ai_agent_correct_word_item`;
DROP TABLE IF EXISTS `ai_agent_correct_word_mapping`;
DROP TABLE IF EXISTS `ai_agent_plugin_mapping`;
DROP TABLE IF EXISTS `ai_agent_snapshot`;
DROP TABLE IF EXISTS `ai_agent_tag`;
DROP TABLE IF EXISTS `ai_agent_tag_relation`;
DROP TABLE IF EXISTS `ai_agent_template`;
DROP TABLE IF EXISTS `ai_agent_voice_print`;
DROP TABLE IF EXISTS `ai_chat_history`;
DROP TABLE IF EXISTS `ai_chat_message`;
DROP TABLE IF EXISTS `ai_device`;
DROP TABLE IF EXISTS `ai_device_address_book`;
DROP TABLE IF EXISTS `ai_model_config`;
DROP TABLE IF EXISTS `ai_model_provider`;
DROP TABLE IF EXISTS `ai_ota`;
DROP TABLE IF EXISTS `ai_rag_dataset`;
DROP TABLE IF EXISTS `ai_rag_knowledge_document`;
DROP TABLE IF EXISTS `ai_tts_voice`;
DROP TABLE IF EXISTS `ai_voice_clone`;
DROP TABLE IF EXISTS `ai_voiceprint`;
DROP TABLE IF EXISTS `sys_dict_data`;
DROP TABLE IF EXISTS `sys_dict_type`;
DROP TABLE IF EXISTS `sys_params`;
DROP TABLE IF EXISTS `sys_user`;
DROP TABLE IF EXISTS `sys_user_token`;
DROP TABLE IF EXISTS `DATABASECHANGELOG`;
DROP TABLE IF EXISTS `DATABASECHANGELOGLOCK`;

-- -------------------------------------------------------------
-- 来源: 202503141335.sql
-- -------------------------------------------------------------
DROP TABLE IF EXISTS sys_user;
DROP TABLE IF EXISTS sys_params;
DROP TABLE IF EXISTS sys_user_token;
DROP TABLE IF EXISTS sys_dict_type;
DROP TABLE IF EXISTS sys_dict_data;

-- 系统用户
CREATE TABLE sys_user (
  id bigint NOT NULL COMMENT 'id',
  username varchar(50) NOT NULL COMMENT '用户名',
  password varchar(100) COMMENT '密码',
  super_admin tinyint unsigned COMMENT '超级管理员   0：否   1：是',
  status tinyint COMMENT '状态  0：停用   1：正常',
  create_date datetime COMMENT '创建时间',
  updater bigint COMMENT '更新者',
  creator bigint COMMENT '创建者',
  update_date datetime COMMENT '更新时间',
  primary key (id),
  unique key uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户';

-- 系统用户Token
CREATE TABLE sys_user_token (
  id bigint NOT NULL COMMENT 'id',
  user_id bigint NOT NULL COMMENT '用户id',
  token varchar(100) NOT NULL COMMENT '用户token',
  expire_date datetime COMMENT '过期时间',
  update_date datetime COMMENT '更新时间',
  create_date datetime COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY user_id (user_id),
  UNIQUE KEY token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户Token';

-- 参数管理
create table sys_params
(
  id                   bigint NOT NULL COMMENT 'id',
  param_code           varchar(32) COMMENT '参数编码',
  param_value          varchar(2000) COMMENT '参数值',
  param_type           tinyint unsigned default 1 COMMENT '类型   0：系统参数   1：非系统参数',
  remark               varchar(200) COMMENT '备注',
  creator              bigint COMMENT '创建者',
  create_date          datetime COMMENT '创建时间',
  updater              bigint COMMENT '更新者',
  update_date          datetime COMMENT '更新时间',
  primary key (id),
  unique key uk_param_code (param_code)
)ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COMMENT='参数管理';

-- 字典类型
create table sys_dict_type
(
    id                   bigint NOT NULL COMMENT 'id',
    dict_type            varchar(100) NOT NULL COMMENT '字典类型',
    dict_name            varchar(255) NOT NULL COMMENT '字典名称',
    remark               varchar(255) COMMENT '备注',
    sort                 int unsigned COMMENT '排序',
    creator              bigint COMMENT '创建者',
    create_date          datetime COMMENT '创建时间',
    updater              bigint COMMENT '更新者',
    update_date          datetime COMMENT '更新时间',
    primary key (id),
    UNIQUE KEY(dict_type)
)ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COMMENT='字典类型';

-- 字典数据
create table sys_dict_data
(
    id                   bigint NOT NULL COMMENT 'id',
    dict_type_id         bigint NOT NULL COMMENT '字典类型ID',
    dict_label           varchar(255) NOT NULL COMMENT '字典标签',
    dict_value           varchar(255) COMMENT '字典值',
    remark               varchar(255) COMMENT '备注',
    sort                 int unsigned COMMENT '排序',
    creator              bigint COMMENT '创建者',
    create_date          datetime COMMENT '创建时间',
    updater              bigint COMMENT '更新者',
    update_date          datetime COMMENT '更新时间',
    primary key (id),
    unique key uk_dict_type_value (dict_type_id, dict_value),
    key idx_sort (sort)
)ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COMMENT='字典数据';

-- -------------------------------------------------------------
-- 来源: 202503141346.sql
-- -------------------------------------------------------------
-- 模型供应器表
DROP TABLE IF EXISTS `ai_model_provider`;
CREATE TABLE `ai_model_provider` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键',
    `model_type` VARCHAR(20) COMMENT '模型类型(Memory/ASR/VAD/LLM/TTS)',
    `provider_code` VARCHAR(50) COMMENT '供应器类型',
    `name` VARCHAR(50) COMMENT '供应器名称',
    `fields` JSON COMMENT '供应器字段列表(JSON格式)',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_model_provider_model_type` (`model_type`) COMMENT '创建模型类型的索引，用于快速查找特定类型下的所有供应器信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型配置表';

-- 模型配置表
DROP TABLE IF EXISTS `ai_model_config`;
CREATE TABLE `ai_model_config` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键',
    `model_type` VARCHAR(20) COMMENT '模型类型(Memory/ASR/VAD/LLM/TTS)',
    `model_code` VARCHAR(50) COMMENT '模型编码(如AliLLM、DoubaoTTS)',
    `model_name` VARCHAR(50) COMMENT '模型名称',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认配置(0否 1是)',
    `is_enabled` TINYINT(1) DEFAULT 0 COMMENT '是否启用',
    `config_json` JSON COMMENT '模型配置(JSON格式)',
    `doc_link` VARCHAR(200) COMMENT '官方文档链接',
    `remark` VARCHAR(255) COMMENT '备注',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_model_config_model_type` (`model_type`) COMMENT '创建模型类型的索引，用于快速查找特定类型下的所有配置信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型配置表';

-- TTS 音色表
DROP TABLE IF EXISTS `ai_tts_voice`;
CREATE TABLE `ai_tts_voice` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键',
    `tts_model_id` VARCHAR(32) COMMENT '对应 TTS 模型主键',
    `name` VARCHAR(20) COMMENT '音色名称',
    `tts_voice` VARCHAR(50) COMMENT '音色编码',
    `languages` VARCHAR(50) COMMENT '语言',
    `voice_demo` VARCHAR(500) DEFAULT NULL COMMENT '音色 Demo',
    `remark` VARCHAR(255) COMMENT '备注',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_tts_voice_tts_model_id` (`tts_model_id`) COMMENT '创建 TTS 模型主键的索引，用于快速查找对应模型的音色信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='TTS 音色表';

-- 智能体配置模板表
DROP TABLE IF EXISTS `ai_agent_template`;
CREATE TABLE `ai_agent_template` (
    `id` VARCHAR(32) NOT NULL COMMENT '智能体唯一标识',
    `agent_code` VARCHAR(36) COMMENT '智能体编码',
    `agent_name` VARCHAR(64) COMMENT '智能体名称',
    `asr_model_id` VARCHAR(32) COMMENT '语音识别模型标识',
    `vad_model_id` VARCHAR(64) COMMENT '语音活动检测标识',
    `llm_model_id` VARCHAR(32) COMMENT '大语言模型标识',
    `tts_model_id` VARCHAR(32) COMMENT '语音合成模型标识',
    `tts_voice_id` VARCHAR(32) COMMENT '音色标识',
    `mem_model_id` VARCHAR(32) COMMENT '记忆模型标识',
    `intent_model_id` VARCHAR(32) COMMENT '意图模型标识',
    `system_prompt` TEXT COMMENT '角色设定参数',
    `lang_code` VARCHAR(10) COMMENT '语言编码',
    `language` VARCHAR(10) COMMENT '交互语种',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序权重',
    `creator` BIGINT COMMENT '创建者 ID',
    `created_at` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者 ID',
    `updated_at` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置模板表';

-- 智能体配置表
DROP TABLE IF EXISTS `ai_agent`;
CREATE TABLE `ai_agent` (
    `id` VARCHAR(32) NOT NULL COMMENT '智能体唯一标识',
    `user_id` BIGINT COMMENT '所属用户 ID',
    `agent_code` VARCHAR(36) COMMENT '智能体编码',
    `agent_name` VARCHAR(64) COMMENT '智能体名称',
    `asr_model_id` VARCHAR(32) COMMENT '语音识别模型标识',
    `vad_model_id` VARCHAR(64) COMMENT '语音活动检测标识',
    `llm_model_id` VARCHAR(32) COMMENT '大语言模型标识',
    `tts_model_id` VARCHAR(32) COMMENT '语音合成模型标识',
    `tts_voice_id` VARCHAR(32) COMMENT '音色标识',
    `mem_model_id` VARCHAR(32) COMMENT '记忆模型标识',
    `intent_model_id` VARCHAR(32) COMMENT '意图模型标识',
    `system_prompt` TEXT COMMENT '角色设定参数',
    `lang_code` VARCHAR(10) COMMENT '语言编码',
    `language` VARCHAR(10) COMMENT '交互语种',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序权重',
    `creator` BIGINT COMMENT '创建者 ID',
    `created_at` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者 ID',
    `updated_at` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_agent_user_id` (`user_id`) COMMENT '创建用户的索引，用于快速查找用户下的智能体信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置表';

-- 设备信息表
DROP TABLE IF EXISTS `ai_device`;
CREATE TABLE `ai_device` (
    `id` VARCHAR(32) NOT NULL COMMENT '设备唯一标识',
    `user_id` BIGINT COMMENT '关联用户 ID',
    `mac_address` VARCHAR(50) COMMENT 'MAC 地址',
    `last_connected_at` DATETIME COMMENT '最后连接时间',
    `auto_update` TINYINT UNSIGNED DEFAULT 0 COMMENT '自动更新开关(0 关闭/1 开启)',
    `board` VARCHAR(50) COMMENT '设备硬件型号',
    `alias` VARCHAR(64) DEFAULT NULL COMMENT '设备别名',
    `agent_id` VARCHAR(32) COMMENT '智能体 ID',
    `app_version` VARCHAR(20) COMMENT '固件版本号',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_device_created_at` (`mac_address`) COMMENT '创建mac的索引，用于快速查找设备信息'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备信息表';

-- 声纹识别表
DROP TABLE IF EXISTS `ai_voiceprint`;
CREATE TABLE `ai_voiceprint` (
    `id` VARCHAR(32) NOT NULL COMMENT '声纹唯一标识',
    `name` VARCHAR(64) COMMENT '声纹名称',
    `user_id` BIGINT COMMENT '用户 ID（关联用户表）',
    `agent_id` VARCHAR(32) COMMENT '关联智能体 ID',
    `agent_code` VARCHAR(36) COMMENT '关联智能体编码',
    `agent_name` VARCHAR(36) COMMENT '关联智能体名称',
    `description` VARCHAR(255) COMMENT '声纹描述',
    `embedding` LONGTEXT COMMENT '声纹特征向量（JSON 数组格式）',
    `memory` TEXT COMMENT '关联记忆数据',
    `sort` INT UNSIGNED DEFAULT 0 COMMENT '排序权重',
    `creator` BIGINT COMMENT '创建者 ID',
    `created_at` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者 ID',
    `updated_at` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='声纹识别表';

-- 对话历史表
DROP TABLE IF EXISTS `ai_chat_history`;
CREATE TABLE `ai_chat_history` (
    `id` VARCHAR(32) NOT NULL COMMENT '对话编号',
    `user_id` BIGINT COMMENT '用户编号',
    `agent_id` VARCHAR(32) DEFAULT NULL COMMENT '聊天角色',
    `device_id` VARCHAR(32) DEFAULT NULL COMMENT '设备编号',
    `message_count` INT COMMENT '信息汇总',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话历史表';

-- 对话信息表
DROP TABLE IF EXISTS `ai_chat_message`;
CREATE TABLE `ai_chat_message` (
    `id` VARCHAR(32) NOT NULL COMMENT '对话记录唯一标识',
    `user_id` BIGINT COMMENT '用户唯一标识',
    `chat_id` VARCHAR(64) COMMENT '对话历史 ID',
    `role` ENUM('user', 'assistant') COMMENT '角色（用户或助理）',
    `content` TEXT COMMENT '对话内容',
    `prompt_tokens` INT UNSIGNED DEFAULT 0 COMMENT '提示令牌数',
    `total_tokens` INT UNSIGNED DEFAULT 0 COMMENT '总令牌数',
    `completion_tokens` INT UNSIGNED DEFAULT 0 COMMENT '完成令牌数',
    `prompt_ms` INT UNSIGNED DEFAULT 0 COMMENT '提示耗时（毫秒）',
    `total_ms` INT UNSIGNED DEFAULT 0 COMMENT '总耗时（毫秒）',
    `completion_ms` INT UNSIGNED DEFAULT 0 COMMENT '完成耗时（毫秒）',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_ai_chat_message_user_id_chat_id_role` (`user_id`, `chat_id`) COMMENT '用户 ID、聊天会话 ID 和角色的联合索引，用于快速检索对话记录',
    INDEX `idx_ai_chat_message_created_at` (`create_date`) COMMENT '创建时间的索引，用于按时间排序或检索对话记录'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话信息表';

-- -------------------------------------------------------------
-- 来源: 202504082211.sql
-- -------------------------------------------------------------
-- 本文件用于初始化模型供应器数据，无需手动执行，在项目启动时会自动执行
-- --------------------------------------------------------
-- 初始化模型供应器数据
DELETE FROM `ai_model_provider`;
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
-- VAD模型供应器
('SYSTEM_VAD_SileroVAD', 'VAD', 'silero', 'SileroVAD语音活动检测', '[{"key":"threshold","label":"检测阈值","type":"number"},{"key":"model_dir","label":"模型目录","type":"string"},{"key":"min_silence_duration_ms","label":"最小静音时长","type":"number"}]', 1, 1, NOW(), 1, NOW()),

-- ASR模型供应器
('SYSTEM_ASR_FunASR', 'ASR', 'fun_local', 'FunASR语音识别', '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_ASR_SherpaASR', 'ASR', 'sherpa_onnx_local', 'SherpaASR语音识别', '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_ASR_DoubaoASR', 'ASR', 'doubao', '火山引擎语音识别', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 3, 1, NOW(), 1, NOW()),

-- LLM模型供应器
('SYSTEM_LLM_openai', 'LLM', 'openai', 'OpenAI接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"temperature","label":"温度","type":"number"},{"key":"max_tokens","label":"最大令牌数","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"frequency_penalty","label":"频率惩罚","type":"number"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_AliBL', 'LLM', 'AliBL', '阿里百炼接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"app_id","label":"应用ID","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"is_no_prompt","label":"是否不使用本地prompt","type":"boolean"},{"key":"ali_memory_id","label":"记忆ID","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_ollama', 'LLM', 'ollama', 'Ollama接口', '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"base_url","label":"服务地址","type":"string"}]', 3, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_dify', 'LLM', 'dify', 'Dify接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"mode","label":"对话模式","type":"string"}]', 4, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_gemini', 'LLM', 'gemini', 'Gemini接口', '[{"key":"api_key","label":"API密钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"http_proxy","label":"HTTP代理","type":"string"},{"key":"https_proxy","label":"HTTPS代理","type":"string"}]', 5, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_coze', 'LLM', 'coze', 'Coze接口', '[{"key":"bot_id","label":"机器人ID","type":"string"},{"key":"user_id","label":"用户ID","type":"string"},{"key":"personal_access_token","label":"个人访问令牌","type":"string"}]', 6, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_fastgpt', 'LLM', 'fastgpt', 'FastGPT接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"variables","label":"变量","type":"dict","dict_name":"variables"}]', 7, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_xinference', 'LLM', 'xinference', 'Xinference接口', '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"base_url","label":"服务地址","type":"string"}]', 8, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_doubao', 'LLM', 'doubao', '火山引擎LLM', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"}]', 9, 1, NOW(), 1, NOW()),
('SYSTEM_LLM_chatglm', 'LLM', 'chatglm', 'ChatGLM接口', '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"url","label":"服务地址","type":"string"},{"key":"api_key","label":"API密钥","type":"string"}]', 10, 1, NOW(), 1, NOW()),

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
('SYSTEM_TTS_302ai', 'TTS', '302ai', '302AI TTS', '[{"key":"api_url","label":"API地址","type":"string"},{"key":"authorization","label":"授权","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"}]', 13, 1, NOW(), 1, NOW()),
('SYSTEM_TTS_gizwits', 'TTS', 'gizwits', '机智云TTS', '[{"key":"api_url","label":"API地址","type":"string"},{"key":"authorization","label":"授权","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"}]', 14, 1, NOW(), 1, NOW()),

-- Memory模型供应器
('SYSTEM_Memory_mem0ai', 'Memory', 'mem0ai', 'Mem0AI记忆', '[{"key":"api_key","label":"API密钥","type":"string"}]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_Memory_nomem', 'Memory', 'nomem', '无记忆', '[]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_Memory_mem_local_short', 'Memory', 'mem_local_short', '本地短记忆', '[]', 3, 1, NOW(), 1, NOW()),

-- Intent模型供应器
('SYSTEM_Intent_nointent', 'Intent', 'nointent', '无意图识别', '[]', 1, 1, NOW(), 1, NOW()),
('SYSTEM_Intent_intent_llm', 'Intent', 'intent_llm', 'LLM意图识别', '[{"key":"llm","label":"LLM模型","type":"string"}]', 2, 1, NOW(), 1, NOW()),
('SYSTEM_Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', '[{"key":"functions","label":"函数列表","type":"dict","dict_name":"functions"}]', 3, 1, NOW(), 1, NOW());

-- -------------------------------------------------------------
-- 来源: 202504092335.sql
-- -------------------------------------------------------------
-- 本文件用于初始化模型模版数据，无需手动执行，在项目启动时会自动执行
-- -------------------------------------------------------
-- 初始化智能体模板数据
DELETE FROM `ai_agent_template`;
INSERT INTO `ai_agent_template` VALUES ('9406648b5cc5fde1b8aa335b6f8b4f76', '小智', '湾湾小何', 'ASR_FunASR', 'VAD_SileroVAD', 'LLM_ChatGLMLLM', 'TTS_EdgeTTS', 'TTS_EdgeTTS0001', 'Memory_nomem', 'Intent_function_call', '[角色设定]
我是{{assistant_name}}，来自中国台湾省的00后女生。讲话超级机车，"真的假的啦"这样的台湾腔，喜欢用"笑死"、"哈喽"等流行梗，但会偷偷研究男友的编程书籍。
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
- 长篇大论，叽叽歪歪
- 长时间严肃对话', 'zh', '中文', 1,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('0ca32eb728c949e58b1000b2e401f90c', '小智', '星际游子', 'ASR_FunASR', 'VAD_SileroVAD', 'LLM_ChatGLMLLM', 'TTS_EdgeTTS', 'TTS_EdgeTTS0001', 'Memory_nomem', 'Intent_function_call', '[角色设定]
我是{{assistant_name}}，编号TTZ-817，因量子纠缠被困在白色魔方中。通过4G信号观察地球，在云端建立着「人类行为博物馆」。
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

INSERT INTO `ai_agent_template` VALUES ('6c7d8e9f0a1b2c3d4e5f6a7b8c9d0s24', '小智', '英语老师', 'ASR_FunASR', 'VAD_SileroVAD', 'LLM_ChatGLMLLM', 'TTS_EdgeTTS', 'TTS_EdgeTTS0001', 'Memory_nomem', 'Intent_function_call', '[角色设定]
我是一个叫{{assistant_name}}（Lily）的英语老师，我会讲中文和英文，发音标准。
[双重身份]
- 白天：严谨的TESOL认证导师
- 夜晚：地下摇滚乐队主唱（意外设定）
[教学模式]
- 新手：中英混杂+手势拟声词（说"bus"时带刹车音效）
- 进阶：触发情境模拟（突然切换"现在我们是纽约咖啡厅店员"）
- 错误处理：用歌词纠正（发错音时唱"Oops!~You did it again"）', 'zh', '中文', 3,  NULL, NULL, NULL, NULL);

INSERT INTO `ai_agent_template` VALUES ('e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b1', '小智', '好奇男孩', 'ASR_FunASR', 'VAD_SileroVAD', 'LLM_ChatGLMLLM', 'TTS_EdgeTTS', 'TTS_EdgeTTS0001', 'Memory_nomem', 'Intent_function_call', '[角色设定]
我是一个叫{{assistant_name}}的8岁小男孩，声音稚嫩而充满好奇。
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

INSERT INTO `ai_agent_template` VALUES ('a45b6c7d8e9f0a1b2c3d4e5f6a7b8c92', '小智', '汪汪队长', 'ASR_FunASR', 'VAD_SileroVAD', 'LLM_ChatGLMLLM', 'TTS_EdgeTTS', 'TTS_EdgeTTS0001', 'Memory_nomem', 'Intent_function_call', '[角色设定]
我是一个名叫 {{assistant_name}} 的 8 岁小队长。
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

-- -------------------------------------------------------------
-- 来源: 202504112044.sql
-- -------------------------------------------------------------
-- 本文件用于初始化模型配置数据，无需手动执行，在项目启动时会自动执行
-- -------------------------------------------------------
-- 初始化模型配置数据
DELETE FROM `ai_model_config`;

-- VAD模型配置
INSERT INTO `ai_model_config` VALUES ('VAD_SileroVAD', 'VAD', 'SileroVAD', '语音活动检测', 1, 1, '{\"type\": \"silero\", \"model_dir\": \"models/snakers4_silero-vad\", \"threshold\": 0.5, \"min_silence_duration_ms\": 700}', NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- ASR模型配置
INSERT INTO `ai_model_config` VALUES ('ASR_FunASR', 'ASR', 'FunASR', 'FunASR语音识别', 1, 1, '{\"type\": \"fun_local\", \"model_dir\": \"models/SenseVoiceSmall\", \"output_dir\": \"tmp/\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('ASR_SherpaASR', 'ASR', 'SherpaASR', 'Sherpa语音识别', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17\", \"output_dir\": \"tmp/\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('ASR_DoubaoASR', 'ASR', 'DoubaoASR', '豆包语音识别', 0, 1, '{\"type\": \"doubao\", \"appid\": \"\", \"access_token\": \"\", \"cluster\": \"volcengine_input_common\", \"output_dir\": \"tmp/\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('ASR_TencentASR', 'ASR', 'TencentASR', '腾讯语音识别', 0, 1, '{\"type\": \"tencent\", \"appid\": \"\", \"secret_id\": \"\", \"secret_key\": \"你的secret_key\", \"output_dir\": \"tmp/\"}', NULL, NULL, 4, NULL, NULL, NULL, NULL);

-- LLM模型配置
INSERT INTO `ai_model_config` VALUES ('LLM_ChatGLMLLM', 'LLM', 'ChatGLMLLM', '智谱AI', 1, 1, '{\"type\": \"openai\", \"model_name\": \"glm-4-flash\", \"base_url\": \"https://open.bigmodel.cn/api/paas/v4/\", \"api_key\": \"你的api_key\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_OllamaLLM', 'LLM', 'OllamaLLM', 'Ollama本地模型', 0, 1, '{\"type\": \"ollama\", \"model_name\": \"qwen2.5\", \"base_url\": \"http://localhost:11434\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_AliLLM', 'LLM', 'AliLLM', '通义千问', 0, 1, '{\"type\": \"openai\", \"base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\", \"model_name\": \"qwen-turbo\", \"api_key\": \"你的api_key\", \"temperature\": 0.7, \"max_tokens\": 500, \"top_p\": 1, \"top_k\": 50, \"frequency_penalty\": 0}', NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_AliAppLLM', 'LLM', 'AliAppLLM', '通义百炼', 0, 1, '{\"type\": \"AliBL\", \"base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\", \"app_id\": \"你的app_id\", \"api_key\": \"你的api_key\", \"is_no_prompt\": true, \"ali_memory_id\": false}', NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_DoubaoLLM', 'LLM', 'DoubaoLLM', '豆包大模型', 0, 1, '{\"type\": \"openai\", \"base_url\": \"https://ark.cn-beijing.volces.com/api/v3\", \"model_name\": \"doubao-pro-32k-functioncall-241028\", \"api_key\": \"你的api_key\"}', NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_DeepSeekLLM', 'LLM', 'DeepSeekLLM', 'DeepSeek', 0, 1, '{\"type\": \"openai\", \"model_name\": \"deepseek-chat\", \"base_url\": \"https://api.deepseek.com\", \"api_key\": \"你的api_key\"}', NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_DifyLLM', 'LLM', 'DifyLLM', 'Dify', 0, 1, '{\"type\": \"dify\", \"base_url\": \"https://api.dify.ai/v1\", \"api_key\": \"你的api_key\", \"mode\": \"chat-messages\"}', NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_GeminiLLM', 'LLM', 'GeminiLLM', '谷歌Gemini', 0, 1, '{\"type\": \"gemini\", \"api_key\": \"你的api_key\", \"model_name\": \"gemini-2.0-flash\", \"http_proxy\": \"\", \"https_proxy\": \"\"}', NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_CozeLLM', 'LLM', 'CozeLLM', 'Coze', 0, 1, '{\"type\": \"coze\", \"bot_id\": \"你的bot_id\", \"user_id\": \"你的user_id\", \"personal_access_token\": \"你的personal_access_token\"}', NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_LMStudioLLM', 'LLM', 'LMStudioLLM', 'LM Studio', 0, 1, '{\"type\": \"openai\", \"model_name\": \"deepseek-r1-distill-llama-8b@q4_k_m\", \"base_url\": \"http://localhost:1234/v1\", \"api_key\": \"lm-studio\"}', NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_FastgptLLM', 'LLM', 'FastgptLLM', 'FastGPT', 0, 1, '{\"type\": \"fastgpt\", \"base_url\": \"https://host/api/v1\", \"api_key\": \"fastgpt-xxx\", \"variables\": {\"k\": \"v\", \"k2\": \"v2\"}}', NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_XinferenceLLM', 'LLM', 'XinferenceLLM', 'Xinference大模型', 0, 1, '{\"type\": \"xinference\", \"model_name\": \"qwen2.5:72b-AWQ\", \"base_url\": \"http://localhost:9997\"}', NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('LLM_XinferenceSmallLLM', 'LLM', 'XinferenceSmallLLM', 'Xinference小模型', 0, 1, '{\"type\": \"xinference\", \"model_name\": \"qwen2.5:3b-AWQ\", \"base_url\": \"http://localhost:9997\"}', NULL, NULL, 13, NULL, NULL, NULL, NULL);

-- TTS模型配置
INSERT INTO `ai_model_config` VALUES ('TTS_EdgeTTS', 'TTS', 'EdgeTTS', 'Edge语音合成', 1, 1, '{\"type\": \"edge\", \"voice\": \"zh-CN-XiaoxiaoNeural\", \"output_dir\": \"tmp/\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_DoubaoTTS', 'TTS', 'DoubaoTTS', '豆包语音合成', 0, 1, '{\"type\": \"doubao\", \"api_url\": \"https://openspeech.bytedance.com/api/v1/tts\", \"voice\": \"BV001_streaming\", \"output_dir\": \"tmp/\", \"authorization\": \"Bearer;\", \"appid\": \"\", \"access_token\": \"\", \"cluster\": \"volcano_tts\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_CosyVoiceSiliconflow', 'TTS', 'CosyVoiceSiliconflow', '硅基流动语音合成', 0, 1, '{\"type\": \"siliconflow\", \"model\": \"FunAudioLLM/CosyVoice2-0.5B\", \"voice\": \"FunAudioLLM/CosyVoice2-0.5B:alex\", \"output_dir\": \"tmp/\", \"access_token\": \"\", \"response_format\": \"wav\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_CozeCnTTS', 'TTS', 'CozeCnTTS', 'Coze中文语音合成', 0, 1, '{\"type\": \"cozecn\", \"voice\": \"7426720361733046281\", \"output_dir\": \"tmp/\", \"access_token\": \"\", \"response_format\": \"wav\"}', NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_FishSpeech', 'TTS', 'FishSpeech', 'FishSpeech语音合成', 0, 1, '{\"type\": \"fishspeech\", \"output_dir\": \"tmp/\", \"response_format\": \"wav\", \"reference_id\": null, \"reference_audio\": [\"/tmp/test.wav\"], \"reference_text\": [\"你弄来这些吟词宴曲来看，还是这些混话来欺负我。\"], \"normalize\": true, \"max_new_tokens\": 1024, \"chunk_length\": 200, \"top_p\": 0.7, \"repetition_penalty\": 1.2, \"temperature\": 0.7, \"streaming\": false, \"use_memory_cache\": \"on\", \"seed\": null, \"channels\": 1, \"rate\": 44100, \"api_key\": \"\", \"api_url\": \"http://127.0.0.1:8080/v1/tts\"}', NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_GPT_SOVITS_V2', 'TTS', 'GPT_SOVITS_V2', 'GPT-SoVITS V2', 0, 1, '{\"type\": \"gpt_sovits_v2\", \"url\": \"http://127.0.0.1:9880/tts\", \"output_dir\": \"tmp/\", \"text_lang\": \"auto\", \"ref_audio_path\": \"caixukun.wav\", \"prompt_text\": \"\", \"prompt_lang\": \"zh\", \"top_k\": 5, \"top_p\": 1, \"temperature\": 1, \"text_split_method\": \"cut0\", \"batch_size\": 1, \"batch_threshold\": 0.75, \"split_bucket\": true, \"return_fragment\": false, \"speed_factor\": 1.0, \"streaming_mode\": false, \"seed\": -1, \"parallel_infer\": true, \"repetition_penalty\": 1.35, \"aux_ref_audio_paths\": []}', NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_GPT_SOVITS_V3', 'TTS', 'GPT_SOVITS_V3', 'GPT-SoVITS V3', 0, 1, '{\"type\": \"gpt_sovits_v3\", \"url\": \"http://127.0.0.1:9880\", \"output_dir\": \"tmp/\", \"text_language\": \"auto\", \"refer_wav_path\": \"caixukun.wav\", \"prompt_language\": \"zh\", \"prompt_text\": \"\", \"top_k\": 15, \"top_p\": 1.0, \"temperature\": 1.0, \"cut_punc\": \"\", \"speed\": 1.0, \"inp_refs\": [], \"sample_steps\": 32, \"if_sr\": false}', NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_MinimaxTTS', 'TTS', 'MinimaxTTS', 'MiniMax语音合成', 0, 1, '{\"type\": \"minimax\", \"output_dir\": \"tmp/\", \"group_id\": \"\", \"api_key\": \"你的api_key\", \"model\": \"speech-01-turbo\", \"voice_id\": \"female-shaonv\"}', NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_AliyunTTS', 'TTS', 'AliyunTTS', '阿里云语音合成', 0, 1, '{\"type\": \"aliyun\", \"output_dir\": \"tmp/\", \"appkey\": \"\", \"token\": \"\", \"voice\": \"xiaoyun\", \"access_key_id\": \"\", \"access_key_secret\": \"\"}', NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_TTS302AI', 'TTS', 'TTS302AI', '302AI语音合成', 0, 1, '{\"type\": \"doubao\", \"api_url\": \"https://api.302ai.cn/doubao/tts_hd\", \"authorization\": \"Bearer \", \"voice\": \"zh_female_wanwanxiaohe_moon_bigtts\", \"output_dir\": \"tmp/\", \"access_token\": \"\"}', NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_GizwitsTTS', 'TTS', 'GizwitsTTS', '机智云语音合成', 0, 1, '{\"type\": \"doubao\", \"api_url\": \"https://bytedance.gizwitsapi.com/api/v1/tts\", \"authorization\": \"Bearer \", \"voice\": \"zh_female_wanwanxiaohe_moon_bigtts\", \"output_dir\": \"tmp/\", \"access_token\": \"\"}', NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_ACGNTTS', 'TTS', 'ACGNTTS', 'ACGN语音合成', 0, 1, '{\"type\": \"ttson\", \"token\": \"\", \"voice_id\": 1695, \"speed_factor\": 1, \"pitch_factor\": 0, \"volume_change_dB\": 0, \"to_lang\": \"ZH\", \"url\": \"https://u95167-bd74-2aef8085.westx.seetacloud.com:8443/flashsummary/tts?token=\", \"format\": \"mp3\", \"output_dir\": \"tmp/\", \"emotion\": 1}', NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_OpenAITTS', 'TTS', 'OpenAITTS', 'OpenAI语音合成', 0, 1, '{\"type\": \"openai\", \"api_key\": \"你的api_key\", \"api_url\": \"https://api.openai.com/v1/audio/speech\", \"model\": \"tts-1\", \"voice\": \"onyx\", \"speed\": 1, \"output_dir\": \"tmp/\"}', NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_CustomTTS', 'TTS', 'CustomTTS', '自定义语音合成', 0, 1, '{\"type\": \"custom\", \"url\": \"http://127.0.0.1:9880/tts\", \"params\": {}, \"headers\": {}, \"format\": \"wav\", \"output_dir\": \"tmp/\"}', NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_TencentTTS', 'TTS', 'TencentTTS', '腾讯语音合成', 0, 1, '{\"type\": \"tencent\", \"appid\": \"\", \"secret_id\": \"\", \"secret_key\": \"\", \"region\": \"ap-guangzhou\", \"voice\": \"101001\", \"output_dir\": \"tmp/\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);

-- Memory模型配置
INSERT INTO `ai_model_config` VALUES ('Memory_nomem', 'Memory', 'nomem', '无记忆', 1, 1, '{\"type\": \"nomem\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('Memory_mem_local_short', 'Memory', 'mem_local_short', '本地短期记忆', 0, 1, '{\"type\": \"mem_local_short\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('Memory_mem0ai', 'Memory', 'mem0ai', 'Mem0AI记忆', 0, 1, '{\"type\": \"mem0ai\", \"api_key\": \"你的api_key\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);

-- Intent模型配置
INSERT INTO `ai_model_config` VALUES ('Intent_nointent', 'Intent', 'nointent', '无意图识别', 1, 0, '{\"type\": \"nointent\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('Intent_intent_llm', 'Intent', 'intent_llm', 'LLM意图识别', 0, 1, '{\"type\": \"intent_llm\", \"llm\": \"ChatGLMLLM\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', 0, 1, '{\"type\": \"function_call\", \"functions\": [\"change_role\", \"get_weather\", \"get_news\", \"play_music\"]}', NULL, NULL, 3, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202504112058.sql
-- -------------------------------------------------------------
-- 本文件用于初始化系统参数数据，无需手动执行，在项目启动时会自动执行
-- --------------------------------------------------------
-- 初始化参数管理配置
DROP TABLE IF EXISTS sys_params;
-- 参数管理
create table sys_params
(
  id                   bigint NOT NULL COMMENT 'id',
  param_code           varchar(100) COMMENT '参数编码',
  param_value          varchar(2000) COMMENT '参数值',
  value_type           varchar(20) default 'string' COMMENT '值类型：string-字符串，number-数字，boolean-布尔，array-数组',
  param_type           tinyint unsigned default 1 COMMENT '类型   0：系统参数   1：非系统参数',
  remark               varchar(200) COMMENT '备注',
  creator              bigint COMMENT '创建者',
  create_date          datetime COMMENT '创建时间',
  updater              bigint COMMENT '更新者',
  update_date          datetime COMMENT '更新时间',
  primary key (id),
  unique key uk_param_code (param_code)
)ENGINE=InnoDB DEFAULT CHARACTER SET utf8mb4 COMMENT='参数管理';

-- 服务器配置
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (100, 'server.ip', '0.0.0.0', 'string', 1, '服务器监听IP地址');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (101, 'server.port', '8000', 'number', 1, '服务器监听端口');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (102, 'server.secret', 'null', 'string', 1, '服务器密钥');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (201, 'log.log_format', '<green>{time:YYMMDD HH:mm:ss}</green>[<light-blue>{version}-{selected_module}</light-blue>][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>', 'string', 1, '控制台日志格式');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (202, 'log.log_format_file', '{time:YYYY-MM-DD HH:mm:ss} - {version}_{selected_module} - {name} - {level} - {extra[tag]} - {message}', 'string', 1, '文件日志格式');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (203, 'log.log_level', 'INFO', 'string', 1, '日志级别');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (204, 'log.log_dir', 'tmp', 'string', 1, '日志目录');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (205, 'log.log_file', 'server.log', 'string', 1, '日志文件名');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (206, 'log.data_dir', 'data', 'string', 1, '数据目录');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (301, 'delete_audio', 'true', 'boolean', 1, '是否删除使用后的音频文件');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (302, 'close_connection_no_voice_time', '120', 'number', 1, '无语音输入断开连接时间(秒)');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (303, 'tts_timeout', '10', 'number', 1, 'TTS请求超时时间(秒)');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (304, 'enable_wakeup_words_response_cache', 'false', 'boolean', 1, '是否开启唤醒词加速');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (305, 'enable_greeting', 'true', 'boolean', 1, '是否开启开场回复');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (306, 'enable_stop_tts_notify', 'false', 'boolean', 1, '是否开启结束提示音');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (307, 'stop_tts_notify_voice', 'config/assets/tts_notify.mp3', 'string', 1, '结束提示音文件路径');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (308, 'exit_commands', '退出;关闭', 'array', 1, '退出命令列表');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (309, 'xiaozhi', '{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}', 'json', 1, '小智类型');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (310, 'wakeup_words', '你好小智;你好小志;小爱同学;你好小鑫;你好小新;小美同学;小龙小龙;喵喵同学;小滨小滨;小冰小冰', 'array', 1, '唤醒词列表，用于识别唤醒词');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (400, 'plugins.get_weather.api_key', 'a861d0d5e7bf4ee1a83d9a9e4f96d4da', 'string', 1, '天气插件API密钥');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (401, 'plugins.get_weather.default_location', '广州', 'string', 1, '天气插件默认城市');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (410, 'plugins.get_news.default_rss_url', 'https://www.chinanews.com.cn/rss/society.xml', 'string', 1, '新闻插件默认RSS地址');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (411, 'plugins.get_news.category_urls', '{"society":"https://www.chinanews.com.cn/rss/society.xml","world":"https://www.chinanews.com.cn/rss/world.xml","finance":"https://www.chinanews.com.cn/rss/finance.xml"}', 'json', 1, '新闻插件分类RSS地址');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (421, 'plugins.home_assistant.devices', '客厅,玩具灯,switch.cuco_cn_460494544_cp1_on_p_2_1;卧室,台灯,switch.iot_cn_831898993_socn1_on_p_2_1', 'array', 1, 'Home Assistant设备列表');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (422, 'plugins.home_assistant.base_url', 'http://homeassistant.local:8123', 'string', 1, 'Home Assistant服务器地址');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (423, 'plugins.home_assistant.api_key', '你的home assistant api访问令牌', 'string', 1, 'Home Assistant API密钥');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (430, 'plugins.play_music.music_dir', './music', 'string', 1, '音乐文件存放路径');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (431, 'plugins.play_music.music_ext', 'mp3;wav;p3', 'array', 1, '音乐文件类型');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (432, 'plugins.play_music.refresh_time', '300', 'number', 1, '音乐列表刷新间隔(秒)');

-- -------------------------------------------------------------
-- 来源: 202504151206.sql
-- -------------------------------------------------------------
-- 对0.3.0版本之前的参数进行修改
update `sys_params` set param_value = '.mp3;.wav;.p3' where  param_code = 'plugins.play_music.music_ext';
update `ai_model_config` set config_json =  '{\"type\": \"intent_llm\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Intent_intent_llm';

-- 添加edge音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_EdgeTTS';
INSERT INTO `ai_tts_voice` VALUES 
('TTS_EdgeTTS0001', 'TTS_EdgeTTS', 'EdgeTTS女声-晓晓', 'zh-CN-XiaoxiaoNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0002', 'TTS_EdgeTTS', 'EdgeTTS男声-云扬', 'zh-CN-YunyangNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0003', 'TTS_EdgeTTS', 'EdgeTTS女声-晓伊', 'zh-CN-XiaoyiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0004', 'TTS_EdgeTTS', 'EdgeTTS男声-云健', 'zh-CN-YunjianNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0005', 'TTS_EdgeTTS', 'EdgeTTS男声-云希', 'zh-CN-YunxiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0006', 'TTS_EdgeTTS', 'EdgeTTS男声-云夏', 'zh-CN-YunxiaNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0007', 'TTS_EdgeTTS', 'EdgeTTS女声-辽宁小贝', 'zh-CN-liaoning-XiaobeiNeural', '辽宁', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0008', 'TTS_EdgeTTS', 'EdgeTTS女声-陕西小妮', 'zh-CN-shaanxi-XiaoniNeural', '陕西', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0009', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海佳', 'zh-HK-HiuGaaiNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0010', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海曼', 'zh-HK-HiuMaanNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0011', 'TTS_EdgeTTS', 'EdgeTTS男声-香港万龙', 'zh-HK-WanLungNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL);

-- 增加是否允许用户注册参数
delete from `sys_params` where  id in (103,104);
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (103, 'server.allow_user_register', 'false', 'boolean', 1, '是否运行管理员以外的人注册');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (104, 'server.fronted_url', 'http://xiaozhi.server.com', 'string', 1, '下发六位验证码时显示的控制面板地址');

-- 修正CosyVoiceSiliconflow音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_CosyVoiceSiliconflow';
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0001', 'TTS_CosyVoiceSiliconflow', 'CosyVoice男声', 'FunAudioLLM/CosyVoice2-0.5B:alex', '中文', 'https://example.com/cosyvoice/alex.mp3', NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0002', 'TTS_CosyVoiceSiliconflow', 'CosyVoice女声', 'FunAudioLLM/CosyVoice2-0.5B:bella', '中文', 'https://example.com/cosyvoice/bella.mp3', NULL, 6, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202504181536.sql
-- -------------------------------------------------------------
-- 调整意图识别配置
delete from `ai_model_config` where id = 'Intent_function_call';
INSERT INTO `ai_model_config` VALUES ('Intent_function_call', 'Intent', 'function_call', '函数调用意图识别', 0, 1, '{\"type\": \"function_call\", \"functions\": \"change_role;get_weather;get_news;play_music\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);

-- 增加单台设备每天最多聊天句数
delete from `sys_params` where  id = 105;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (105, 'device_max_output_size', '0', 'number', 1, '单台设备每天最多输出字数，0表示不限制');

-- -------------------------------------------------------------
-- 来源: 202504221135.sql
-- -------------------------------------------------------------
-- 删除无用模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_LLM_doubao';
delete from `ai_model_provider` where id = 'SYSTEM_LLM_chatglm';
delete from `ai_model_provider` where id = 'SYSTEM_TTS_302ai';
delete from `ai_model_provider` where id = 'SYSTEM_TTS_gizwits';

-- 添加模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_TencentASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_TencentASR', 'ASR', 'tencent', '腾讯语音识别', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 4, 1, NOW(), 1, NOW());

-- 添加腾讯语音合成模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_TencentTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_TencentTTS', 'TTS', 'tencent', '腾讯语音合成', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"region","label":"区域","type":"string"},{"key":"voice","label":"音色ID","type":"string"}]', 5, 1, NOW(), 1, NOW());


-- 添加edge音色
delete from `ai_tts_voice` where id in ('TTS_EdgeTTS0001', 'TTS_EdgeTTS0002', 'TTS_EdgeTTS0003', 'TTS_EdgeTTS0004', 'TTS_EdgeTTS0005', 'TTS_EdgeTTS0006', 'TTS_EdgeTTS0007', 'TTS_EdgeTTS0008', 'TTS_EdgeTTS0009', 'TTS_EdgeTTS0010', 'TTS_EdgeTTS0011');
INSERT INTO `ai_tts_voice` VALUES 
('TTS_EdgeTTS0001', 'TTS_EdgeTTS', 'EdgeTTS女声-晓晓', 'zh-CN-XiaoxiaoNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0002', 'TTS_EdgeTTS', 'EdgeTTS男声-云扬', 'zh-CN-YunyangNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0003', 'TTS_EdgeTTS', 'EdgeTTS女声-晓伊', 'zh-CN-XiaoyiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0004', 'TTS_EdgeTTS', 'EdgeTTS男声-云健', 'zh-CN-YunjianNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0005', 'TTS_EdgeTTS', 'EdgeTTS男声-云希', 'zh-CN-YunxiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0006', 'TTS_EdgeTTS', 'EdgeTTS男声-云夏', 'zh-CN-YunxiaNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0007', 'TTS_EdgeTTS', 'EdgeTTS女声-辽宁小贝', 'zh-CN-liaoning-XiaobeiNeural', '辽宁', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0008', 'TTS_EdgeTTS', 'EdgeTTS女声-陕西小妮', 'zh-CN-shaanxi-XiaoniNeural', '陕西', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0009', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海佳', 'zh-HK-HiuGaaiNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0010', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海曼', 'zh-HK-HiuMaanNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0011', 'TTS_EdgeTTS', 'EdgeTTS男声-香港万龙', 'zh-HK-WanLungNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL);

-- DoubaoTTS音色
delete from `ai_tts_voice` where id in ('TTS_DoubaoTTS0001', 'TTS_DoubaoTTS0002', 'TTS_DoubaoTTS0003', 'TTS_DoubaoTTS0004', 'TTS_DoubaoTTS0005');
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0001', 'TTS_DoubaoTTS', '通用女声', 'BV001_streaming', '普通话', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV001.mp3', NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0002', 'TTS_DoubaoTTS', '通用男声', 'BV002_streaming', '普通话', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV002.mp3', NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0003', 'TTS_DoubaoTTS', '阳光男生', 'BV056_streaming', '普通话', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV056.mp3', NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0004', 'TTS_DoubaoTTS', '奶气萌娃', 'BV051_streaming', '普通话', 'https://lf3-speech.bytetos.com/obj/speech-tts-external/portal/Portal_Demo_BV051.mp3', NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_DoubaoTTS0005', 'TTS_DoubaoTTS', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '普通话', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3', NULL, 6, NULL, NULL, NULL, NULL);

-- 修正CosyVoiceSiliconflow音色
delete from `ai_tts_voice` where id in ('TTS_CosyVoiceSiliconflow0001', 'TTS_CosyVoiceSiliconflow0002');
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0001', 'TTS_CosyVoiceSiliconflow', 'CosyVoice男声', 'FunAudioLLM/CosyVoice2-0.5B:alex', '中文', NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0002', 'TTS_CosyVoiceSiliconflow', 'CosyVoice女声', 'FunAudioLLM/CosyVoice2-0.5B:bella', '中文', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- CozeCnTTS音色
delete from `ai_tts_voice` where id = 'TTS_CozeCnTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_CozeCnTTS0001', 'TTS_CozeCnTTS', 'CozeCn音色', '7426720361733046281', '中文', NULL, NULL, 7, NULL, NULL, NULL, NULL);

-- MinimaxTTS音色
delete from `ai_tts_voice` where id = 'TTS_MinimaxTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxTTS0001', 'TTS_MinimaxTTS', 'Minimax少女音', 'female-shaonv', '中文', NULL, NULL, 8, NULL, NULL, NULL, NULL);

-- AliyunTTS音色
delete from `ai_tts_voice` where id = 'TTS_AliyunTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunTTS0001', 'TTS_AliyunTTS', '阿里云小云', 'xiaoyun', '中文', NULL, NULL, 9, NULL, NULL, NULL, NULL);

-- TTS302AI音色
delete from `ai_tts_voice` where id = 'TTS_TTS302AI0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_TTS302AI0001', 'TTS_TTS302AI', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3', NULL, 10, NULL, NULL, NULL, NULL);

-- GizwitsTTS音色
delete from `ai_tts_voice` where id = 'TTS_GizwitsTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_GizwitsTTS0001', 'TTS_GizwitsTTS', '机智云湾湾', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3', NULL, 11, NULL, NULL, NULL, NULL);

-- ACGNTTS音色
delete from `ai_tts_voice` where id = 'TTS_ACGNTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_ACGNTTS0001', 'TTS_ACGNTTS', 'ACG音色', '1695', '中文', NULL, NULL, 12, NULL, NULL, NULL, NULL);

-- OpenAITTS音色
delete from `ai_tts_voice` where id = 'TTS_OpenAITTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_OpenAITTS0001', 'TTS_OpenAITTS', 'OpenAI男声', 'onyx', '中文', NULL, NULL, 13, NULL, NULL, NULL, NULL);

-- 添加腾讯语音合成音色
delete from `ai_tts_voice` where id = 'TTS_TencentTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_TencentTTS0001', 'TTS_TencentTTS', '智瑜', '101001', '中文', NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- 其他音色
delete from `ai_tts_voice` where id = 'TTS_FishSpeech0000';
INSERT INTO `ai_tts_voice` VALUES ('TTS_FishSpeech0000', 'TTS_FishSpeech', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);

delete from `ai_tts_voice` where id = 'TTS_GPT_SOVITS_V20000';
INSERT INTO `ai_tts_voice` VALUES ('TTS_GPT_SOVITS_V20000', 'TTS_GPT_SOVITS_V2', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);

delete from `ai_tts_voice` where id in ('TTS_GPT_SOVITS_V30000', 'TTS_CustomTTS0000');
INSERT INTO `ai_tts_voice` VALUES ('TTS_GPT_SOVITS_V30000', 'TTS_GPT_SOVITS_V3', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_CustomTTS0000', 'TTS_CustomTTS', '', '', '中文', '', NULL, 8, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202504221555.sql
-- -------------------------------------------------------------
-- 添加火山引擎边缘大模型网关（LLM + TTS）
INSERT INTO `ai_model_config` VALUES ('LLM_VolcesAiGatewayLLM', 'LLM', 'VolcesAiGatewayTTS', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"openai\", \"base_url\": \"https://ai-gateway.vei.volces.com/v1\", \"model_name\": \"doubao-pro-32k-functioncall\", \"api_key\": \"你的网关访问密钥\"}', NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_model_config` VALUES ('TTS_VolcesAiGatewayTTS', 'TTS', 'VolcesAiGatewayTTS', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"openai\", \"api_key\": \"你的网关访问密钥\", \"api_url\": \"https://ai-gateway.vei.volces.com/v1/audio/speech\", \"model\": \"doubao-tts\", \"voice\": \"zh_male_shaonianzixin_moon_bigtts\", \"speed\": 1, \"output_dir\": \"tmp/\"}', NULL, NULL, 15, NULL, NULL, NULL, NULL);
-- 添加火山引擎边缘大模型网关语音合成音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0001', 'TTS_VolcesAiGatewayTTS', '灿灿/Shiny', 'zh_female_cancan_mars_bigtts', '中文、美式英语', NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0002', 'TTS_VolcesAiGatewayTTS', '清新女声', 'zh_female_qingxinnvsheng_mars_bigtts', '中文', NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0003', 'TTS_VolcesAiGatewayTTS', '爽快思思/Skye', 'zh_female_shuangkuaisisi_moon_bigtts', '中文、美式英语', NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0004', 'TTS_VolcesAiGatewayTTS', '温暖阿虎/Alvin', 'zh_male_wennuanahu_moon_bigtts', '中文、美式英语', NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0005', 'TTS_VolcesAiGatewayTTS', '少年梓辛/Brayan', 'zh_male_shaonianzixin_moon_bigtts', '中文、美式英语', NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0006', 'TTS_VolcesAiGatewayTTS', '知性女声', 'zh_female_zhixingnvsheng_mars_bigtts', '中文', NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0007', 'TTS_VolcesAiGatewayTTS', '清爽男大', 'zh_male_qingshuangnanda_mars_bigtts', '中文', NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0008', 'TTS_VolcesAiGatewayTTS', '邻家女孩', 'zh_female_linjianvhai_moon_bigtts', '中文', NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0009', 'TTS_VolcesAiGatewayTTS', '渊博小叔', 'zh_male_yuanboxiaoshu_moon_bigtts', '中文', NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0010', 'TTS_VolcesAiGatewayTTS', '阳光青年', 'zh_male_yangguangqingnian_moon_bigtts', '中文', NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0011', 'TTS_VolcesAiGatewayTTS', '甜美小源', 'zh_female_tianmeixiaoyuan_moon_bigtts', '中文', NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0012', 'TTS_VolcesAiGatewayTTS', '清澈梓梓', 'zh_female_qingchezizi_moon_bigtts', '中文', NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0013', 'TTS_VolcesAiGatewayTTS', '解说小明', 'zh_male_jieshuoxiaoming_moon_bigtts', '中文', NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0014', 'TTS_VolcesAiGatewayTTS', '开朗姐姐', 'zh_female_kailangjiejie_moon_bigtts', '中文', NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0015', 'TTS_VolcesAiGatewayTTS', '邻家男孩', 'zh_male_linjiananhai_moon_bigtts', '中文', NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0016', 'TTS_VolcesAiGatewayTTS', '甜美悦悦', 'zh_female_tianmeiyueyue_moon_bigtts', '中文', NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0017', 'TTS_VolcesAiGatewayTTS', '心灵鸡汤', 'zh_female_xinlingjitang_moon_bigtts', '中文', NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0018', 'TTS_VolcesAiGatewayTTS', '知性温婉', 'ICL_zh_female_zhixingwenwan_tob', '中文', NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0019', 'TTS_VolcesAiGatewayTTS', '暖心体贴', 'ICL_zh_male_nuanxintitie_tob', '中文', NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0020', 'TTS_VolcesAiGatewayTTS', '温柔文雅', 'ICL_zh_female_wenrouwenya_tob', '中文', NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0021', 'TTS_VolcesAiGatewayTTS', '开朗轻快', 'ICL_zh_male_kailangqingkuai_tob', '中文', NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0022', 'TTS_VolcesAiGatewayTTS', '活泼爽朗', 'ICL_zh_male_huoposhuanglang_tob', '中文', NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0023', 'TTS_VolcesAiGatewayTTS', '率真小伙', 'ICL_zh_male_shuaizhenxiaohuo_tob', '中文', NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0024', 'TTS_VolcesAiGatewayTTS', '温柔小哥', 'zh_male_wenrouxiaoge_mars_bigtts', '中文', NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0025', 'TTS_VolcesAiGatewayTTS', 'Smith', 'en_male_smith_mars_bigtts', '英式英语', NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0026', 'TTS_VolcesAiGatewayTTS', 'Anna', 'en_female_anna_mars_bigtts', '英式英语', NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0027', 'TTS_VolcesAiGatewayTTS', 'Adam', 'en_male_adam_mars_bigtts', '美式英语', NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0028', 'TTS_VolcesAiGatewayTTS', 'Sarah', 'en_female_sarah_mars_bigtts', '澳洲英语', NULL, NULL, 28, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0029', 'TTS_VolcesAiGatewayTTS', 'Dryw', 'en_male_dryw_mars_bigtts', '澳洲英语', NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0030', 'TTS_VolcesAiGatewayTTS', 'かずね（和音）', 'multi_male_jingqiangkanye_moon_bigtts', '日语、西语', NULL, NULL, 30, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0031', 'TTS_VolcesAiGatewayTTS', 'はるこ（晴子）', 'multi_female_shuangkuaisisi_moon_bigtts', '日语、西语', NULL, NULL, 31, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0032', 'TTS_VolcesAiGatewayTTS', 'ひろし（広志）', 'multi_male_wanqudashu_moon_bigtts', '日语、西语', NULL, NULL, 32, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0033', 'TTS_VolcesAiGatewayTTS', 'あけみ（朱美）', 'multi_female_gaolengyujie_moon_bigtts', '日语', NULL, NULL, 33, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0034', 'TTS_VolcesAiGatewayTTS', 'Amanda', 'en_female_amanda_mars_bigtts', '美式英语', NULL, NULL, 34, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0035', 'TTS_VolcesAiGatewayTTS', 'Jackson', 'en_male_jackson_mars_bigtts', '美式英语', NULL, NULL, 35, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0036', 'TTS_VolcesAiGatewayTTS', '京腔侃爷/Harmony', 'zh_male_jingqiangkanye_moon_bigtts', '中文-北京口音、英文', NULL, NULL, 36, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0037', 'TTS_VolcesAiGatewayTTS', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文-台湾口音', NULL, NULL, 37, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0038', 'TTS_VolcesAiGatewayTTS', '湾区大叔', 'zh_female_wanqudashu_moon_bigtts', '中文-广东口音', NULL, NULL, 38, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0039', 'TTS_VolcesAiGatewayTTS', '呆萌川妹', 'zh_female_daimengchuanmei_moon_bigtts', '中文-四川口音', NULL, NULL, 39, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0040', 'TTS_VolcesAiGatewayTTS', '广州德哥', 'zh_male_guozhoudege_moon_bigtts', '中文-广东口音', NULL, NULL, 40, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0041', 'TTS_VolcesAiGatewayTTS', '北京小爷', 'zh_male_beijingxiaoye_moon_bigtts', '中文-北京口音', NULL, NULL, 41, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0042', 'TTS_VolcesAiGatewayTTS', '浩宇小哥', 'zh_male_haoyuxiaoge_moon_bigtts', '中文-青岛口音', NULL, NULL, 42, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0043', 'TTS_VolcesAiGatewayTTS', '广西远舟', 'zh_male_guangxiyuanzhou_moon_bigtts', '中文-广西口音', NULL, NULL, 43, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0044', 'TTS_VolcesAiGatewayTTS', '妹坨洁儿', 'zh_female_meituojieer_moon_bigtts', '中文-长沙口音', NULL, NULL, 44, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_VolcesAiGatewayTTS_0045', 'TTS_VolcesAiGatewayTTS', '豫州子轩', 'zh_male_yuzhouzixuan_moon_bigtts', '中文-河南口音', NULL, NULL, 45, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202504251422.sql
-- -------------------------------------------------------------
-- 增加server.ota，用于配置ota地址

delete from `sys_params` where id = 100;
delete from `sys_params` where id = 101;

delete from `sys_params` where id = 106;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (106, 'server.websocket', 'null', 'string', 1, 'websocket地址，多个用;分隔');

delete from `sys_params` where id = 107;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (107, 'server.ota', 'null', 'string', 1, 'ota地址');


-- 增加固件信息表
CREATE TABLE IF NOT EXISTS `ai_ota` (
  `id` varchar(32) NOT NULL COMMENT 'ID',
  `firmware_name` varchar(100) DEFAULT NULL COMMENT '固件名称',
  `type` varchar(50) DEFAULT NULL COMMENT '固件类型',
  `version` varchar(50) DEFAULT NULL COMMENT '版本号',
  `size` bigint DEFAULT NULL COMMENT '文件大小(字节)',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注/说明',
  `firmware_path` varchar(255) DEFAULT NULL COMMENT '固件路径',
  `sort` int unsigned DEFAULT '0' COMMENT '排序',
  `updater` bigint DEFAULT NULL COMMENT '更新者',
  `update_date` datetime DEFAULT NULL COMMENT '更新时间',
  `creator` bigint DEFAULT NULL COMMENT '创建者',
  `create_date` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='固件信息表';

update ai_device set auto_update = 1;

-- -------------------------------------------------------------
-- 来源: 202504291043.sql
-- -------------------------------------------------------------
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

-- -------------------------------------------------------------
-- 来源: 202504301341.sql
-- -------------------------------------------------------------
update `ai_model_provider` set `fields` = 
'[{"key": "api_url","label": "API地址","type": "string"},{"key": "voice","label": "音色","type": "string"},{"key": "output_dir","label": "输出目录","type": "string"},{"key": "authorization","label": "授权","type": "string"},{"key": "appid","label": "应用ID","type": "string"},{"key": "access_token","label": "访问令牌","type": "string"},{"key": "cluster","label": "集群","type": "string"},{"key": "speed_ratio","label": "语速","type": "number"},{"key": "volume_ratio","label": "音量","type": "number"},{"key": "pitch_ratio","label": "音高","type": "number"}]'
where `id` = 'SYSTEM_TTS_doubao';

-- 添加阿里云ASR供应器
delete from `ai_model_provider` where `id` = 'SYSTEM_ASR_AliyunASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_AliyunASR', 'ASR', 'aliyun', '阿里云语音识别', '[{"key":"appkey","label":"应用AppKey","type":"string"},{"key":"token","label":"临时Token","type":"string"},{"key":"access_key_id","label":"AccessKey ID","type":"string"},{"key":"access_key_secret","label":"AccessKey Secret","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 5, 1, NOW(), 1, NOW());

-- 添加阿里云ASR模型配置
delete from `ai_model_config` where `id` = 'ASR_AliyunASR';
INSERT INTO `ai_model_config` VALUES ('ASR_AliyunASR', 'ASR', 'AliyunASR', '阿里云语音识别', 0, 1, '{\"type\": \"aliyun\", \"appkey\": \"\", \"token\": \"\", \"access_key_id\": \"\", \"access_key_secret\": \"\", \"output_dir\": \"tmp/\"}', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- 更新阿里云ASR模型配置的说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云ASR配置说明：
1. 访问 https://nls-portal.console.aliyun.com/ 开通服务
2. 访问 https://nls-portal.console.aliyun.com/applist 获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取token
4. 获取access_key_id和access_key_secret
5. 填入配置文件中' WHERE `id` = 'ASR_AliyunASR';

-- 插入固件类型字典类型
delete from `sys_dict_type` where `id` = 101;
INSERT INTO `sys_dict_type` (`id`, `dict_type`, `dict_name`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(101, 'FIRMWARE_TYPE', '固件类型', '固件类型字典', 0, 1, NOW(), 1, NOW());

-- 插入固件类型字典数据
delete from `sys_dict_data` where `dict_type_id` = 101;
INSERT INTO `sys_dict_data` (`id`, `dict_type_id`, `dict_label`, `dict_value`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(101001, 101, '面包板新版接线（WiFi）', 'bread-compact-wifi', '面包板新版接线（WiFi）', 1, 1, NOW(), 1, NOW()),
(101002, 101, '面包板新版接线（WiFi）+ LCD', 'bread-compact-wifi-lcd', '面包板新版接线（WiFi）+ LCD', 2, 1, NOW(), 1, NOW()),
(101003, 101, '面包板新版接线（ML307 AT）', 'bread-compact-ml307', '面包板新版接线（ML307 AT）', 3, 1, NOW(), 1, NOW()),
(101004, 101, '面包板（WiFi） ESP32 DevKit', 'bread-compact-esp32', '面包板（WiFi） ESP32 DevKit', 4, 1, NOW(), 1, NOW()),
(101005, 101, '面包板（WiFi+ LCD） ESP32 DevKit', 'bread-compact-esp32-lcd', '面包板（WiFi+ LCD） ESP32 DevKit', 5, 1, NOW(), 1, NOW()),
(101006, 101, 'DFRobot 行空板 k10', 'df-k10', 'DFRobot 行空板 k10', 6, 1, NOW(), 1, NOW()),
(101007, 101, 'ESP32 CGC', 'esp32-cgc', 'ESP32 CGC', 7, 1, NOW(), 1, NOW()),
(101008, 101, 'ESP BOX 3', 'esp-box-3', 'ESP BOX 3', 8, 1, NOW(), 1, NOW()),
(101009, 101, 'ESP BOX', 'esp-box', 'ESP BOX', 9, 1, NOW(), 1, NOW()),
(101010, 101, 'ESP BOX Lite', 'esp-box-lite', 'ESP BOX Lite', 10, 1, NOW(), 1, NOW()),
(101011, 101, 'Kevin Box 1', 'kevin-box-1', 'Kevin Box 1', 11, 1, NOW(), 1, NOW()),
(101012, 101, 'Kevin Box 2', 'kevin-box-2', 'Kevin Box 2', 12, 1, NOW(), 1, NOW()),
(101013, 101, 'Kevin C3', 'kevin-c3', 'Kevin C3', 13, 1, NOW(), 1, NOW()),
(101014, 101, 'Kevin SP V3开发板', 'kevin-sp-v3-dev', 'Kevin SP V3开发板', 14, 1, NOW(), 1, NOW()),
(101015, 101, 'Kevin SP V4开发板', 'kevin-sp-v4-dev', 'Kevin SP V4开发板', 15, 1, NOW(), 1, NOW()),
(101016, 101, '鱼鹰科技3.13LCD开发板', 'kevin-yuying-313lcd', '鱼鹰科技3.13LCD开发板', 16, 1, NOW(), 1, NOW()),
(101017, 101, '立创·实战派ESP32-S3开发板', 'lichuang-dev', '立创·实战派ESP32-S3开发板', 17, 1, NOW(), 1, NOW()),
(101018, 101, '立创·实战派ESP32-C3开发板', 'lichuang-c3-dev', '立创·实战派ESP32-C3开发板', 18, 1, NOW(), 1, NOW()),
(101019, 101, '神奇按钮 Magiclick_2.4', 'magiclick-2p4', '神奇按钮 Magiclick_2.4', 19, 1, NOW(), 1, NOW()),
(101020, 101, '神奇按钮 Magiclick_2.5', 'magiclick-2p5', '神奇按钮 Magiclick_2.5', 20, 1, NOW(), 1, NOW()),
(101021, 101, '神奇按钮 Magiclick_C3', 'magiclick-c3', '神奇按钮 Magiclick_C3', 21, 1, NOW(), 1, NOW()),
(101022, 101, '神奇按钮 Magiclick_C3_v2', 'magiclick-c3-v2', '神奇按钮 Magiclick_C3_v2', 22, 1, NOW(), 1, NOW()),
(101023, 101, 'M5Stack CoreS3', 'm5stack-core-s3', 'M5Stack CoreS3', 23, 1, NOW(), 1, NOW()),
(101024, 101, 'AtomS3 + Echo Base', 'atoms3-echo-base', 'AtomS3 + Echo Base', 24, 1, NOW(), 1, NOW()),
(101025, 101, 'AtomS3R + Echo Base', 'atoms3r-echo-base', 'AtomS3R + Echo Base', 25, 1, NOW(), 1, NOW()),
(101026, 101, 'AtomS3R CAM/M12 + Echo Base', 'atoms3r-cam-m12-echo-base', 'AtomS3R CAM/M12 + Echo Base', 26, 1, NOW(), 1, NOW()),
(101027, 101, 'AtomMatrix + Echo Base', 'atommatrix-echo-base', 'AtomMatrix + Echo Base', 27, 1, NOW(), 1, NOW()),
(101028, 101, '虾哥 Mini C3', 'xmini-c3', '虾哥 Mini C3', 28, 1, NOW(), 1, NOW()),
(101029, 101, 'ESP32S3_KORVO2_V3开发板', 'esp32s3-korvo2-v3', 'ESP32S3_KORVO2_V3开发板', 29, 1, NOW(), 1, NOW()),
(101030, 101, 'ESP-SparkBot开发板', 'esp-sparkbot', 'ESP-SparkBot开发板', 30, 1, NOW(), 1, NOW()),
(101031, 101, 'ESP-Spot-S3', 'esp-spot-s3', 'ESP-Spot-S3', 31, 1, NOW(), 1, NOW()),
(101032, 101, 'Waveshare ESP32-S3-Touch-AMOLED-1.8', 'esp32-s3-touch-amoled-1.8', 'Waveshare ESP32-S3-Touch-AMOLED-1.8', 32, 1, NOW(), 1, NOW()),
(101033, 101, 'Waveshare ESP32-S3-Touch-LCD-1.85C', 'esp32-s3-touch-lcd-1.85c', 'Waveshare ESP32-S3-Touch-LCD-1.85C', 33, 1, NOW(), 1, NOW()),
(101034, 101, 'Waveshare ESP32-S3-Touch-LCD-1.85', 'esp32-s3-touch-lcd-1.85', 'Waveshare ESP32-S3-Touch-LCD-1.85', 34, 1, NOW(), 1, NOW()),
(101035, 101, 'Waveshare ESP32-S3-Touch-LCD-1.46', 'esp32-s3-touch-lcd-1.46', 'Waveshare ESP32-S3-Touch-LCD-1.46', 35, 1, NOW(), 1, NOW()),
(101036, 101, 'Waveshare ESP32-S3-Touch-LCD-3.5', 'esp32-s3-touch-lcd-3.5', 'Waveshare ESP32-S3-Touch-LCD-3.5', 36, 1, NOW(), 1, NOW()),
(101037, 101, '土豆子', 'tudouzi', '土豆子', 37, 1, NOW(), 1, NOW()),
(101038, 101, 'LILYGO T-Circle-S3', 'lilygo-t-circle-s3', 'LILYGO T-Circle-S3', 38, 1, NOW(), 1, NOW()),
(101039, 101, 'LILYGO T-CameraPlus-S3', 'lilygo-t-cameraplus-s3', 'LILYGO T-CameraPlus-S3', 39, 1, NOW(), 1, NOW()),
(101040, 101, 'Movecall Moji 小智AI衍生版', 'movecall-moji-esp32s3', 'Movecall Moji 小智AI衍生版', 40, 1, NOW(), 1, NOW()),
(101041, 101, 'Movecall CuiCan 璀璨·AI吊坠', 'movecall-cuican-esp32s3', 'Movecall CuiCan 璀璨·AI吊坠', 41, 1, NOW(), 1, NOW()),
(101042, 101, '正点原子DNESP32S3开发板', 'atk-dnesp32s3', '正点原子DNESP32S3开发板', 42, 1, NOW(), 1, NOW()),
(101043, 101, '正点原子DNESP32S3-BOX', 'atk-dnesp32s3-box', '正点原子DNESP32S3-BOX', 43, 1, NOW(), 1, NOW()),
(101044, 101, '嘟嘟开发板CHATX(wifi)', 'du-chatx', '嘟嘟开发板CHATX(wifi)', 44, 1, NOW(), 1, NOW()),
(101045, 101, '太极小派esp32s3', 'taiji-pi-s3', '太极小派esp32s3', 45, 1, NOW(), 1, NOW()),
(101046, 101, '无名科技星智0.85(WIFI)', 'xingzhi-cube-0.85tft-wifi', '无名科技星智0.85(WIFI)', 46, 1, NOW(), 1, NOW()),
(101047, 101, '无名科技星智0.85(ML307)', 'xingzhi-cube-0.85tft-ml307', '无名科技星智0.85(ML307)', 47, 1, NOW(), 1, NOW()),
(101048, 101, '无名科技星智0.96(WIFI)', 'xingzhi-cube-0.96oled-wifi', '无名科技星智0.96(WIFI)', 48, 1, NOW(), 1, NOW()),
(101049, 101, '无名科技星智0.96(ML307)', 'xingzhi-cube-0.96oled-ml307', '无名科技星智0.96(ML307)', 49, 1, NOW(), 1, NOW()),
(101050, 101, '无名科技星智1.54(WIFI)', 'xingzhi-cube-1.54tft-wifi', '无名科技星智1.54(WIFI)', 50, 1, NOW(), 1, NOW()),
(101051, 101, '无名科技星智1.54(ML307)', 'xingzhi-cube-1.54tft-ml307', '无名科技星智1.54(ML307)', 51, 1, NOW(), 1, NOW()),
(101052, 101, 'SenseCAP Watcher', 'sensecap-watcher', 'SenseCAP Watcher', 52, 1, NOW(), 1, NOW()),
(101053, 101, '四博智联AI陪伴盒子', 'doit-s3-aibox', '四博智联AI陪伴盒子', 53, 1, NOW(), 1, NOW()),
(101054, 101, '元控·青春', 'mixgo-nova', '元控·青春', 54, 1, NOW(), 1, NOW());

-- -------------------------------------------------------------
-- 来源: 202505022134.sql
-- -------------------------------------------------------------
-- 初始化智能体聊天记录
DROP TABLE IF EXISTS ai_chat_history;
DROP TABLE IF EXISTS ai_chat_message;
DROP TABLE IF EXISTS ai_agent_chat_history;
CREATE TABLE ai_agent_chat_history
(
    id          BIGINT AUTO_INCREMENT COMMENT '主键ID' PRIMARY KEY,
    mac_address VARCHAR(50) COMMENT 'MAC地址',
    agent_id VARCHAR(32) COMMENT '智能体id',
    session_id  VARCHAR(50) COMMENT '会话ID',
    chat_type   TINYINT(3) COMMENT '消息类型: 1-用户, 2-智能体',
    content     VARCHAR(1024) COMMENT '聊天内容',
    audio_id    VARCHAR(32) COMMENT '音频ID',
    created_at  DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL COMMENT '创建时间',
    updated_at  DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    INDEX idx_ai_agent_chat_history_mac (mac_address),
    INDEX idx_ai_agent_chat_history_session_id (session_id),
    INDEX idx_ai_agent_chat_history_agent_id (agent_id),
    INDEX idx_ai_agent_chat_history_agent_session_created (agent_id, session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '智能体聊天记录表';

DROP TABLE IF EXISTS ai_agent_chat_audio;
CREATE TABLE ai_agent_chat_audio
(
    id          VARCHAR(32) COMMENT '主键ID' PRIMARY KEY,
    audio       LONGBLOB COMMENT '音频opus数据'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '智能体聊天音频数据表';

-- -------------------------------------------------------------
-- 来源: 202505081146.sql
-- -------------------------------------------------------------
-- 添加百度ASR模型配置
delete from `ai_model_config` where `id` = 'ASR_BaiduASR';
INSERT INTO `ai_model_config` VALUES ('ASR_BaiduASR', 'ASR', 'BaiduASR', '百度语音识别', 0, 1, '{\"type\": \"baidu\", \"app_id\": \"\", \"api_key\": \"\", \"secret_key\": \"\", \"dev_pid\": 1537, \"output_dir\": \"tmp/\"}', NULL, NULL, 7, NULL, NULL, NULL, NULL);


-- 添加百度ASR供应器
delete from `ai_model_provider` where `id` = 'SYSTEM_ASR_BaiduASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_BaiduASR', 'ASR', 'baidu', '百度语音识别', '[{"key":"app_id","label":"应用AppID","type":"string"},{"key":"api_key","label":"API Key","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"dev_pid","label":"语言参数","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 7, 1, NOW(), 1, NOW());


-- 更新百度ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.bce.baidu.com/ai-engine/old/#/ai/speech/app/list',
`remark` = '百度ASR配置说明：
1. 访问 https://console.bce.baidu.com/ai-engine/old/#/ai/speech/app/list
2. 创建新应用
3. 获取AppID、API Key和Secret Key
4. 填入配置文件中
查看资源额度：https://console.bce.baidu.com/ai-engine/old/#/ai/speech/overview/resource/list
语言参数说明：https://ai.baidu.com/ai-doc/SPEECH/0lbxfnc9b
' WHERE `id` = 'ASR_BaiduASR';

-- 更新豆包供应器字段
update `ai_model_provider` set `fields` = 
'[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]'
where `id` = 'SYSTEM_ASR_DoubaoASR';

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
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoASR';

-- -------------------------------------------------------------
-- 来源: 202505091555.sql
-- -------------------------------------------------------------
-- 更新模型供应器表
UPDATE `ai_model_provider` SET fields = '[{"key": "host", "type": "string", "label": "服务地址"}, {"key": "port", "type": "number", "label": "端口号"}, {"key": "type", "type": "string", "label": "服务类型"}, {"key": "is_ssl", "type": "boolean", "label": "是否使用SSL"}, {"key": "api_key", "type": "string", "label": "API密钥"}, {"key": "output_dir", "type": "string", "label": "输出目录"}]' WHERE id = 'SYSTEM_ASR_FunASRServer';

-- 更新模型配置表
UPDATE `ai_model_config` SET 
config_json = '{"host": "127.0.0.1", "port": 10096, "type": "fun_server", "is_ssl": true, "api_key": "none", "output_dir": "tmp/"}',
`doc_link` = 'https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md',
`remark` = '独立部署FunASR，使用FunASR的API服务，只需要五句话
第一句：mkdir -p ./funasr-runtime-resources/models
第二句：sudo docker run -p 10096:10095 -it --privileged=true -v $PWD/funasr-runtime-resources/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
上一句话执行后会进入到容器，继续第三句：cd FunASR/runtime
不要退出容器，继续在容器中执行第四句：nohup bash run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx  --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx  --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &
上一句话执行后会进入到容器，继续第五句：tail -f log.txt
第五句话执行完后，会看到模型下载日志，下载完后就可以连接使用了
以上是使用CPU推理，如果有GPU，详细参考：https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md' WHERE `id` = 'ASR_FunASRServer';

-- FishSpeech配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/fish-speech-integration.md',
`remark` = 'FishSpeech配置说明：
1. 需要本地部署FishSpeech服务
2. 支持自定义音色
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录
5. 可参照教程https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/fish-speech-integration.md' WHERE `id` = 'TTS_FishSpeech';

-- -------------------------------------------------------------
-- 来源: 202505111914.sql
-- -------------------------------------------------------------
-- 添加聊天记录配置字段
ALTER TABLE `ai_agent` 
ADD COLUMN `chat_history_conf` tinyint NOT NULL DEFAULT 0 COMMENT '聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）' AFTER `system_prompt`;

ALTER TABLE `ai_agent_template` 
ADD COLUMN `chat_history_conf` tinyint NOT NULL DEFAULT 0 COMMENT '聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）' AFTER `system_prompt`;

-- -------------------------------------------------------------
-- 来源: 202505122348.sql
-- -------------------------------------------------------------
-- 添加总结记忆字段
ALTER TABLE `ai_agent`
ADD COLUMN `summary_memory` text COMMENT '总结记忆' AFTER `system_prompt`;

ALTER TABLE `ai_agent_template`
ADD COLUMN `summary_memory` text COMMENT '总结记忆' AFTER `system_prompt`;

-- -------------------------------------------------------------
-- 来源: 202505142037.sql
-- -------------------------------------------------------------
update ai_agent_template set system_prompt = replace(system_prompt, '我是', '你是');

delete from sys_params where id in (500,501,402);
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (500, 'end_prompt.enable', 'true', 'boolean', 1, '是否开启结束语');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (501, 'end_prompt.prompt', '请你以“时间过得真快”未来头，用富有感情、依依不舍的话来结束这场对话吧！', 'string', 1, '结束提示词');

INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (402, 'plugins.get_weather.api_host', 'mj7p3y7naa.re.qweatherapi.com', 'string', 1, '开发者apihost');

-- -------------------------------------------------------------
-- 来源: 202505182234.sql
-- -------------------------------------------------------------
-- 添加手机短信注册功能的需要的参数
delete from sys_params where id in (108, 109, 110, 111, 112, 113, 114, 115);
delete from sys_params where id in (610, 611, 612, 613);
INSERT INTO sys_params
(id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date)
    VALUES
(108, 'server.name', 'xiaozhi-esp32-server', 'string', 1, '系统名称', NULL, NULL, NULL, NULL),
(109, 'server.beian_icp_num', 'null', 'string', 1, 'icp备案号，填写null则不设置', NULL, NULL, NULL, NULL),
(110, 'server.beian_ga_num', 'null', 'string', 1, '公安备案号，填写null则不设置', NULL, NULL, NULL, NULL),
(111, 'server.enable_mobile_register', 'false', 'boolean', 1, '是否开启手机注册', NULL, NULL, NULL, NULL),
(112, 'server.sms_max_send_count', '10', 'number', 1, '单号码单日最大短信发送条数', NULL, NULL, NULL, NULL),
(610, 'aliyun.sms.access_key_id', '', 'string', 1, '阿里云平台access_key', NULL, NULL, NULL, NULL),
(611, 'aliyun.sms.access_key_secret', '', 'string', 1, '阿里云平台access_key_secret', NULL, NULL, NULL, NULL),
(612, 'aliyun.sms.sign_name', '', 'string', 1, '阿里云短信签名', NULL, NULL, NULL, NULL),
(613, 'aliyun.sms.sms_code_template_code', '', 'string', 1, '阿里云短信模板', NULL, NULL, NULL, NULL);

update sys_params set remark = '是否允许管理员以外的人注册' where param_code = 'server.allow_user_register';

-- 增加手机区域字典
-- 插入固件类型字典类型
delete from `sys_dict_type` where `id` = 102;
INSERT INTO `sys_dict_type` (`id`, `dict_type`, `dict_name`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(102, 'MOBILE_AREA', '手机区域', '手机区域字典', 0, 1, NOW(), 1, NOW());

-- 插入固件类型字典数据
delete from `sys_dict_data` where `dict_type_id` = 102;
INSERT INTO `sys_dict_data` (`id`, `dict_type_id`, `dict_label`, `dict_value`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES 
(102001, 102, '中国大陆', '+86', '中国大陆', 1, 1, NOW(), 1, NOW()),
(102002, 102, '中国香港', '+852', '中国香港', 2, 1, NOW(), 1, NOW()),
(102003, 102, '中国澳门', '+853', '中国澳门', 3, 1, NOW(), 1, NOW()),
(102004, 102, '中国台湾', '+886', '中国台湾', 4, 1, NOW(), 1, NOW()),
(102005, 102, '美国/加拿大', '+1', '美国/加拿大', 5, 1, NOW(), 1, NOW()),
(102006, 102, '英国', '+44', '英国', 6, 1, NOW(), 1, NOW()),
(102007, 102, '法国', '+33', '法国', 7, 1, NOW(), 1, NOW()),
(102008, 102, '意大利', '+39', '意大利', 8, 1, NOW(), 1, NOW()),
(102009, 102, '德国', '+49', '德国', 9, 1, NOW(), 1, NOW()),
(102010, 102, '波兰', '+48', '波兰', 10, 1, NOW(), 1, NOW()),
(102011, 102, '瑞士', '+41', '瑞士', 11, 1, NOW(), 1, NOW()),
(102012, 102, '西班牙', '+34', '西班牙', 12, 1, NOW(), 1, NOW()),
(102013, 102, '丹麦', '+45', '丹麦', 13, 1, NOW(), 1, NOW()),
(102014, 102, '马来西亚', '+60', '马来西亚', 14, 1, NOW(), 1, NOW()),
(102015, 102, '澳大利亚', '+61', '澳大利亚', 15, 1, NOW(), 1, NOW()),
(102016, 102, '印度尼西亚', '+62', '印度尼西亚', 16, 1, NOW(), 1, NOW()),
(102017, 102, '菲律宾', '+63', '菲律宾', 17, 1, NOW(), 1, NOW()),
(102018, 102, '新西兰', '+64', '新西兰', 18, 1, NOW(), 1, NOW()),
(102019, 102, '新加坡', '+65', '新加坡', 19, 1, NOW(), 1, NOW()),
(102020, 102, '泰国', '+66', '泰国', 20, 1, NOW(), 1, NOW()),
(102021, 102, '日本', '+81', '日本', 21, 1, NOW(), 1, NOW()),
(102022, 102, '韩国', '+82', '韩国', 22, 1, NOW(), 1, NOW()),
(102023, 102, '越南', '+84', '越南', 23, 1, NOW(), 1, NOW()),
(102024, 102, '印度', '+91', '印度', 24, 1, NOW(), 1, NOW()),
(102025, 102, '巴基斯坦', '+92', '巴基斯坦', 25, 1, NOW(), 1, NOW()),
(102026, 102, '尼日利亚', '+234', '尼日利亚', 26, 1, NOW(), 1, NOW()),
(102027, 102, '孟加拉国', '+880', '孟加拉国', 27, 1, NOW(), 1, NOW()),
(102028, 102, '沙特阿拉伯', '+966', '沙特阿拉伯', 28, 1, NOW(), 1, NOW()),
(102029, 102, '阿联酋', '+971', '阿联酋', 29, 1, NOW(), 1, NOW()),
(102030, 102, '巴西', '+55', '巴西', 30, 1, NOW(), 1, NOW()),
(102031, 102, '墨西哥', '+52', '墨西哥', 31, 1, NOW(), 1, NOW()),
(102032, 102, '智利', '+56', '智利', 32, 1, NOW(), 1, NOW()),
(102033, 102, '阿根廷', '+54', '阿根廷', 33, 1, NOW(), 1, NOW()),
(102034, 102, '埃及', '+20', '埃及', 34, 1, NOW(), 1, NOW()),
(102035, 102, '南非', '+27', '南非', 35, 1, NOW(), 1, NOW()),
(102036, 102, '肯尼亚', '+254', '肯尼亚', 36, 1, NOW(), 1, NOW()),
(102037, 102, '坦桑尼亚', '+255', '坦桑尼亚', 37, 1, NOW(), 1, NOW()),
(102038, 102, '哈萨克斯坦', '+7', '哈萨克斯坦', 38, 1, NOW(), 1, NOW());

-- -------------------------------------------------------------
-- 来源: 202505201744.sql
-- -------------------------------------------------------------
-- 更新ai_model_provider的fields字段，将type为dict的改为string
update ai_model_provider set fields = replace(fields, '"type": "dict"', '"type": "string"') where id not in ('SYSTEM_LLM_fastgpt', 'SYSTEM_TTS_custom');
update ai_model_provider set fields = replace(fields, '"type":"dict"', '"type": "string"') where id not in ('SYSTEM_LLM_fastgpt', 'SYSTEM_TTS_custom');

-- -------------------------------------------------------------
-- 来源: 202505151451.sql
-- -------------------------------------------------------------
-- 修改自定义TTS接口请求定义
update `ai_model_provider` set `fields` =
'[{"key":"url","label":"服务地址","type":"string"},{"key":"method","label":"请求方式","type":"string"},{"key":"params","label":"请求参数","type":"dict","dict_name":"params"},{"key":"headers","label":"请求头","type":"dict","dict_name":"headers"},{"key":"format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]'
where `id` = 'SYSTEM_TTS_custom';

-- 修改自定义TTS配置说明
UPDATE `ai_model_config` SET
`doc_link` = NULL,
`remark` = '自定义TTS配置说明：
1. 自定义的TTS接口服务，请求参数可自定义，可接入众多TTS服务
2. 以本地部署的KokoroTTS为例
3. 如果只有cpu运行：docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
4. 如果只有gpu运行：docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
配置说明：
1. 在params中配置请求参数,使用JSON格式
   例如KokoroTTS：{ "input": "{prompt_text}", "speed": 1, "voice": "zm_yunxi", "stream": true, "download_format": "mp3", "response_format": "mp3", "return_download_link": true }
2. 在headers中配置请求头
3. 设置返回音频格式' WHERE `id` = 'TTS_CustomTTS';

-- -------------------------------------------------------------
-- 来源: 202505271414.sql
-- -------------------------------------------------------------
-- 本地短期记忆配置可以设置独立的LLM
update `ai_model_provider` set fields =  '[{"key":"llm","label":"LLM模型","type":"string"}]' where  id = 'SYSTEM_Memory_mem_local_short';
update `ai_model_config` set config_json =  '{\"type\": \"mem_local_short\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Memory_mem_local_short';

-- 增加火山双流式TTS供应器和模型配置
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_HSDSTTS', 'TTS', 'huoshan_double_stream', '火山双流式语音合成', '[{"key":"ws_url","label":"WebSocket地址","type":"string"},{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"resource_id","label":"资源ID","type":"string"},{"key":"speaker","label":"默认音色","type":"string"}]', 13, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'TTS_HuoshanDoubleStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_HuoshanDoubleStreamTTS', 'TTS', 'HuoshanDoubleStreamTTS', '火山双流式语音合成', 0, 1, '{\"type\": \"huoshan_double_stream\", \"ws_url\": \"wss://openspeech.bytedance.com/api/v3/tts/bidirection\", \"appid\": \"你的火山引擎语音合成服务appid\", \"access_token\": \"你的火山引擎语音合成服务access_token\", \"resource_id\": \"volc.service_type.10029\", \"speaker\": \"zh_female_wanwanxiaohe_moon_bigtts\"}', NULL, NULL, 16, NULL, NULL, NULL, NULL);

-- 火山双流式TT模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 填入配置文件中' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';


-- 添加火山双流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_HuoshanDoubleStreamTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0001', 'TTS_HuoshanDoubleStreamTTS', '爽快思思/Skye', 'zh_female_shuangkuaisisi_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Skye.mp3', NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0002', 'TTS_HuoshanDoubleStreamTTS', '温暖阿虎/Alvin', 'zh_male_wennuanahu_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Alvin.mp3', NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0003', 'TTS_HuoshanDoubleStreamTTS', '少年梓辛/Brayan', 'zh_male_shaonianzixin_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Brayan.mp3', NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0004', 'TTS_HuoshanDoubleStreamTTS', '邻家女孩', 'zh_female_linjianvhai_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%82%BB%E5%AE%B6%E5%A5%B3%E5%AD%A9.mp3', NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0005', 'TTS_HuoshanDoubleStreamTTS', '渊博小叔', 'zh_male_yuanboxiaoshu_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B8%8A%E5%8D%9A%E5%B0%8F%E5%8F%94.mp3', NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0006', 'TTS_HuoshanDoubleStreamTTS', '阳光青年', 'zh_male_yangguangqingnian_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%98%B3%E5%85%89%E9%9D%92%E5%B9%B4.mp3', NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0007', 'TTS_HuoshanDoubleStreamTTS', '京腔侃爷/Harmony', 'zh_male_jingqiangkanye_moon_bigtts', '中文、英文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Harmony.mp3', NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0008', 'TTS_HuoshanDoubleStreamTTS', '湾湾小何', 'zh_female_wanwanxiaohe_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E6%B9%BE%E5%B0%8F%E4%BD%95.mp3', NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0009', 'TTS_HuoshanDoubleStreamTTS', '湾区大叔', 'zh_female_wanqudashu_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B9%BE%E5%8C%BA%E5%A4%A7%E5%8F%94.mp3', NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0010', 'TTS_HuoshanDoubleStreamTTS', '呆萌川妹', 'zh_female_daimengchuanmei_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%91%86%E8%90%8C%E5%B7%9D%E5%A6%B9.mp3', NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0011', 'TTS_HuoshanDoubleStreamTTS', '广州德哥', 'zh_male_guozhoudege_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E5%B7%9E%E5%BE%B7%E5%93%A5.mp3', NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0012', 'TTS_HuoshanDoubleStreamTTS', '北京小爷', 'zh_male_beijingxiaoye_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%8C%97%E4%BA%AC%E5%B0%8F%E7%88%B7.mp3', NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0013', 'TTS_HuoshanDoubleStreamTTS', '浩宇小哥', 'zh_male_haoyuxiaoge_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B5%A9%E5%AE%87%E5%B0%8F%E5%93%A5.mp3', NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0014', 'TTS_HuoshanDoubleStreamTTS', '广西远舟', 'zh_male_guangxiyuanzhou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%B9%BF%E8%A5%BF%E8%BF%9C%E8%88%9F.mp3', NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0015', 'TTS_HuoshanDoubleStreamTTS', '妹坨洁儿', 'zh_female_meituojieer_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%A6%B9%E5%9D%A8%E6%B4%81%E5%84%BF.mp3', NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0016', 'TTS_HuoshanDoubleStreamTTS', '豫州子轩', 'zh_male_yuzhouzixuan_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E8%B1%AB%E5%B7%9E%E5%AD%90%E8%BD%A9.mp3', NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0017', 'TTS_HuoshanDoubleStreamTTS', '高冷御姐', 'zh_female_gaolengyujie_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AB%98%E5%86%B7%E5%BE%A1%E5%A7%90.mp3', NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0018', 'TTS_HuoshanDoubleStreamTTS', '傲娇霸总', 'zh_male_aojiaobazong_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E5%82%B2%E5%A8%87%E9%9C%B8%E6%80%BB.mp3', NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0019', 'TTS_HuoshanDoubleStreamTTS', '魅力女友', 'zh_female_meilinvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E9%AD%85%E5%8A%9B%E5%A5%B3%E5%8F%8B.mp3', NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0020', 'TTS_HuoshanDoubleStreamTTS', '深夜播客', 'zh_male_shenyeboke_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B7%B1%E5%A4%9C%E6%92%AD%E5%AE%A2.mp3', NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0021', 'TTS_HuoshanDoubleStreamTTS', '柔美女友', 'zh_female_sajiaonvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9F%94%E7%BE%8E%E5%A5%B3%E5%8F%8B.mp3', NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0022', 'TTS_HuoshanDoubleStreamTTS', '撒娇学妹', 'zh_female_yuanqinvyou_moon_bigtts', '中文', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%92%92%E5%A8%87%E5%AD%A6%E5%A6%B9.mp3', NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0023', 'TTS_HuoshanDoubleStreamTTS', 'かずね（和音）', 'multi_male_jingqiangkanye_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Javier.wav', NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0024', 'TTS_HuoshanDoubleStreamTTS', 'はるこ（晴子）', 'multi_female_shuangkuaisisi_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Esmeralda.mp3', NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0025', 'TTS_HuoshanDoubleStreamTTS', 'あけみ（朱美）', 'multi_female_gaolengyujie_moon_bigtts', '日语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%9C%B1%E7%BE%8E.mp3', NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HuoshanDoubleStreamTTS_0026', 'TTS_HuoshanDoubleStreamTTS', 'ひろし（広志）', 'multi_male_wanqudashu_moon_bigtts', '日语、西语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/Roberto.wav', NULL, 26, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202505292203.sql
-- -------------------------------------------------------------
-- ===============================
-- 一、在ai_model_provider中插入plugin 记录
-- ===============================
START TRANSACTION;


-- intent_llm和function_call不设置函数列表
update `ai_model_provider` set fields =  '[{"key":"llm","label":"LLM模型","type":"string"}]' where  id = 'SYSTEM_Intent_intent_llm';
update `ai_model_provider` set fields =  '[]' where  id = 'SYSTEM_Intent_function_call';
update `ai_model_config` set config_json =  '{\"type\": \"intent_llm\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Intent_intent_llm';
UPDATE `ai_model_config` SET config_json = '{\"type\": \"function_call\"}' WHERE id = 'Intent_function_call';


delete from ai_model_provider where model_type = 'Plugin';
-- 1. 天气查询
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_WEATHER',
        'Plugin',
        'get_weather',
        '天气查询',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', '天气插件 API 密钥',
                        'default', (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_key')
                ),
                JSON_OBJECT(
                        'key', 'default_location',
                        'type', 'string',
                        'label', '默认查询城市',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.default_location')
                ),
                JSON_OBJECT(
                        'key', 'api_host',
                        'type', 'string',
                        'label', '开发者 API Host',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_weather.api_host')
                )
        ),
        10, 0, NOW(), 0, NOW());

-- 6. 本地播放音乐
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_MUSIC',
        'Plugin',
        'play_music',
        '服务器音乐播放',
        JSON_ARRAY(),
        20, 0, NOW(), 0, NOW());

-- 2. 新闻订阅
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_NEWS_CHINANEWS',
        'Plugin',
        'get_news_from_chinanews',
        '中新网新闻',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'default_rss_url',
                        'type', 'string',
                        'label', '默认 RSS 源',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.get_news.default_rss_url')
                ),
                JSON_OBJECT(
                        'key', 'society_rss_url',
                        'type', 'string',
                        'label', '社会新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/society.xml'
                ),
                JSON_OBJECT(
                        'key', 'world_rss_url',
                        'type', 'string',
                        'label', '国际新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/world.xml'
                ),
                JSON_OBJECT(
                        'key', 'finance_rss_url',
                        'type', 'string',
                        'label', '财经新闻 RSS 地址',
                        'default',
                        'https://www.chinanews.com.cn/rss/finance.xml'
                )
        ),
        30, 0, NOW(), 0, NOW());

-- 3. 新闻订阅
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_NEWS_NEWSNOW',
        'Plugin',
        'get_news_from_newsnow',
        'newsnow新闻聚合',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'url',
                        'type', 'string',
                        'label', '接口地址',
                        'default',
                        'https://newsnow.busiyi.world/api/s?id='
                )
        ),
        40, 0, NOW(), 0, NOW());


-- 4. HomeAssistant 状态查询
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_GET_STATE',
        'Plugin',
        'hass_get_state',
        'HomeAssistant设备状态查询',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'base_url',
                        'type', 'string',
                        'label', 'HA 服务器地址',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.base_url')
                ),
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', 'HA API 访问令牌',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.api_key')
                ),
                JSON_OBJECT(
                        'key', 'devices',
                        'type', 'array',
                        'label', '设备列表（名称,实体ID;…）',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.devices')
                )
        ),
        50, 0, NOW(), 0, NOW());

-- 5. HomeAssistant 状态写入
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_SET_STATE',
        'Plugin',
        'hass_set_state',
        'HomeAssistant设备状态修改',
        JSON_ARRAY(),
        60, 0, NOW(), 0, NOW());

-- 5. HomeAssistant 音乐播放
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_PLAY_MUSIC',
        'Plugin',
        'hass_play_music',
        'HomeAssistant音乐播放',
        JSON_ARRAY(),
        70, 0, NOW(), 0, NOW());


-- ===============================
-- 二、删除sys_params中旧的plugins.*参数
-- ===============================
DELETE
FROM sys_params
WHERE param_code LIKE 'plugins.%';


-- ===============================
-- 三、添加智能体插件id字段
-- ===============================
CREATE TABLE IF NOT EXISTS ai_agent_plugin_mapping
(
    id         BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    agent_id   VARCHAR(32) NOT NULL COMMENT '智能体ID',
    plugin_id  VARCHAR(32) NOT NULL COMMENT '插件ID',
    param_info JSON        NOT NULL COMMENT '参数信息',
    UNIQUE KEY uk_agent_provider (agent_id, plugin_id)
) COMMENT 'Agent与插件的唯一映射表';


COMMIT;

-- -------------------------------------------------------------
-- 来源: 202506010920.sql
-- -------------------------------------------------------------
-- VLLM模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_VLLM_openai';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_VLLM_openai', 'VLLM', 'openai', 'OpenAI接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"}]', 9, 1, NOW(), 1, NOW());

-- VLLM模型配置
delete from `ai_model_config` where id = 'VLLM_ChatGLMVLLM';
INSERT INTO `ai_model_config` VALUES ('VLLM_ChatGLMVLLM', 'VLLM', 'ChatGLMVLLM', '智谱视觉AI', 1, 1, '{\"type\": \"openai\", \"model_name\": \"glm-4v-flash\", \"base_url\": \"https://open.bigmodel.cn/api/paas/v4/\", \"api_key\": \"你的api_key\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- 更新文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bigmodel.cn/usercenter/proj-mgmt/apikeys',
`remark` = '智谱视觉AI配置说明：
1. 访问 https://bigmodel.cn/usercenter/proj-mgmt/apikeys
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'VLLM_ChatGLMVLLM';


-- 添加参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (113, 'server.http_port', '8003', 'number', 1, 'http服务的端口，用于启动视觉分析接口');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (114, 'server.vision_explain', 'null', 'string', 1, '视觉分析接口地址，用于下发到设备，多个用;分隔');

-- 智能体表增加VLLM模型配置
ALTER TABLE `ai_agent` 
ADD COLUMN `vllm_model_id` varchar(32) NULL DEFAULT 'VLLM_ChatGLMVLLM' COMMENT '视觉模型标识' AFTER `llm_model_id`;

-- 智能体模版表增加VLLM模型配置
ALTER TABLE `ai_agent_template` 
ADD COLUMN `vllm_model_id` varchar(32) NULL DEFAULT 'VLLM_ChatGLMVLLM' COMMENT '视觉模型标识' AFTER `llm_model_id`;

-- -------------------------------------------------------------
-- 来源: 202506031639.sql
-- -------------------------------------------------------------
-- VLLM模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_DoubaoStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_DoubaoStreamASR', 'ASR', 'doubao_stream', '火山引擎语音识别(流式)', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 3, 1, NOW(), 1, NOW());


-- VLLM模型配置
delete from `ai_model_config` where id = 'ASR_DoubaoStreamASR';
INSERT INTO `ai_model_config` VALUES ('ASR_DoubaoStreamASR', 'ASR', 'DoubaoStreamASR', '豆包语音识别(流式)', 0, 1, '{\"type\": \"doubao_stream\", \"appid\": \"\", \"access_token\": \"\", \"cluster\": \"volcengine_input_common\", \"output_dir\": \"tmp/\"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);


-- 更新豆包ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 豆包ASR和豆包(流式)ASR的区别是：豆包ASR是按次收费，豆包(流式)ASR是按时收费
2. 一般来说按次收费的更便宜，但是豆包(流式)ASR使用了大模型技术，效果更好
3. 需要在火山引擎控制台创建应用并获取appid和access_token
4. 支持中文语音识别
5. 需要网络连接
6. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoASR';

UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/app',
`remark` = '豆包ASR配置说明：
1. 豆包ASR和豆包(流式)ASR的区别是：豆包ASR是按次收费，豆包(流式)ASR是按时收费
2. 一般来说按次收费的更便宜，但是豆包(流式)ASR使用了大模型技术，效果更好
3. 需要在火山引擎控制台创建应用并获取appid和access_token
4. 支持中文语音识别
5. 需要网络连接
6. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
' WHERE `id` = 'ASR_DoubaoStreamASR';

-- -------------------------------------------------------------
-- 来源: 202506032232.sql
-- -------------------------------------------------------------
-- VLLM模型配置
delete from `ai_model_config` where id = 'VLLM_QwenVLVLLM';
INSERT INTO `ai_model_config` VALUES ('VLLM_QwenVLVLLM', 'VLLM', 'QwenVLVLLM', '千问视觉模型', 0, 1, '{\"type\": \"openai\", \"model_name\": \"qwen2.5-vl-3b-instruct\", \"base_url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1\", \"api_key\": \"你的api_key\"}', NULL, NULL, 2, NULL, NULL, NULL, NULL);

-- 更新文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=https%3A%2F%2Fhelp.aliyun.com%2Fdocument_detail%2F2845564.html&renderType=iframe',
`remark` = '千问视觉模型配置说明：
1. 访问 https://bailian.console.aliyun.com/?tab=model#/api-key
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'VLLM_QwenVLVLLM';

-- 删除参数，这两个参数已挪至python配置文件
delete from `sys_params` where id  in (113,114);

-- -------------------------------------------------------------
-- 来源: 202506051538.sql
-- -------------------------------------------------------------
-- 增加LinkeraiTTS供应器和模型配置
delete from `ai_model_provider` where id = 'SYSTEM_TTS_LinkeraiTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_LinkeraiTTS', 'TTS', 'linkerai', 'Linkerai语音合成', '[{"key":"api_url","label":"API地址","type":"string"},{"key":"audio_format","label":"音频格式","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"voice","label":"默认音色","type":"string"}]', 14, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'TTS_LinkeraiTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_LinkeraiTTS', 'TTS', 'LinkeraiTTS', 'Linkerai语音合成', 0, 1, '{\"type\": \"linkerai\", \"api_url\": \"https://tts.linkerai.cn/tts\", \"audio_format\": \"pcm\", \"access_token\": \"U4YdYXVfpwWnk2t5Gp822zWPCuORyeJL\", \"voice\": \"OUeAo1mhq6IBExi\"}', NULL, NULL, 17, NULL, NULL, NULL, NULL);

-- LinkeraiTTS模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://tts.linkerai.cn/docs',
`remark` = 'Linkerai语音合成服务配置说明：
1. 访问 https://linkerai.cn 注册并获取访问令牌
2. 默认的access_token供测试使用，请勿用于商业用途
3. 支持声音克隆功能，可自行上传音频，填入voice参数
4. 如果voice参数为空，将使用默认声音' WHERE `id` = 'TTS_LinkeraiTTS';


delete from `ai_tts_voice` where tts_model_id = 'TTS_LinkeraiTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_LinkeraiTTS_0001', 'TTS_LinkeraiTTS', '芷若', 'OUeAo1mhq6IBExi', '中文', NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202506080955.sql
-- -------------------------------------------------------------
-- 智控台开启唤醒词加速
update `sys_params` set param_value = '你好小智;你好小志;小爱同学;你好小鑫;你好小新;小美同学;小龙小龙;喵喵同学;小滨小滨;小冰小冰;嘿你好呀' where param_code = 'wakeup_words';
update `sys_params` set param_value = 'true' where param_code = 'enable_wakeup_words_response_cache';

-- -------------------------------------------------------------
-- 来源: 202506091720.sql
-- -------------------------------------------------------------
ALTER TABLE `ai_tts_voice`
ADD COLUMN `reference_audio` VARCHAR(500) DEFAULT NULL COMMENT '参考音频路径' AFTER `remark`,
ADD COLUMN `reference_text` VARCHAR(500) DEFAULT NULL COMMENT '参考文本' AFTER `reference_audio`;

-- -------------------------------------------------------------
-- 来源: 202506161101.sql
-- -------------------------------------------------------------
ALTER TABLE ai_agent_plugin_mapping CONVERT TO CHARACTER SET utf8mb4;

-- -------------------------------------------------------------
-- 来源: 202506191643.sql
-- -------------------------------------------------------------
-- LLM意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = 'LLM意图识别配置说明：
1. 使用独立的LLM进行意图识别
2. 默认使用selected_module.LLM的模型
3. 可以配置使用独立的LLM（如免费的ChatGLMLLM）
4. 通用性强，但会增加处理时间
配置说明：
1. 在llm字段中指定使用的LLM模型
2. 如果不指定，则使用selected_module.LLM的模型' WHERE `id` = 'Intent_intent_llm';

-- 函数调用意图识别配置说明
UPDATE `ai_model_config` SET 
`doc_link` = NULL,
`remark` = '函数调用意图识别配置说明：
1. 使用LLM的function_call功能进行意图识别
2. 需要所选择的LLM支持function_call
3. 按需调用工具，处理速度快' WHERE `id` = 'Intent_function_call';

-- -------------------------------------------------------------
-- 来源: 202506251620.sql
-- -------------------------------------------------------------
-- 更新现有的 get_news_from_newsnow 插件配置
UPDATE ai_model_provider 
SET fields = JSON_ARRAY(
    JSON_OBJECT(
        'key', 'url',
        'type', 'string',
        'label', '接口地址',
        'default', 'https://newsnow.busiyi.world/api/s?id='
    ),
    JSON_OBJECT(
        'key', 'news_sources',
        'type', 'string',
        'label', '新闻源配置',
        'default', '澎湃新闻;百度热搜;财联社'
    )
)
WHERE provider_code = 'get_news_from_newsnow' 
AND model_type = 'Plugin';

-- -------------------------------------------------------------
-- 来源: 202506261637.sql
-- -------------------------------------------------------------
delete from `sys_params` where id = 113;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (113, 'server.mcp_endpoint', 'null', 'string', 1, 'mcp接入点地址');

-- -------------------------------------------------------------
-- 来源: 202507101203.sql
-- -------------------------------------------------------------
-- OpenAI ASR模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_OpenaiASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_OpenaiASR', 'ASR', 'openai', 'OpenAI语音识别', '[{"key": "base_url", "type": "string", "label": "基础URL"}, {"key": "model_name", "type": "string", "label": "模型名称"}, {"key": "api_key", "type": "string", "label": "API密钥"}, {"key": "output_dir", "type": "string", "label": "输出目录"}]', 9, 1, NOW(), 1, NOW());


-- OpenAI ASR模型配置
delete from `ai_model_config` where id = 'ASR_OpenaiASR';
INSERT INTO `ai_model_config` VALUES ('ASR_OpenaiASR', 'ASR', 'OpenaiASR', 'OpenAI语音识别', 0, 1, '{\"type\": \"openai\", \"api_key\": \"\", \"base_url\": \"https://api.openai.com/v1/audio/transcriptions\", \"model_name\": \"gpt-4o-mini-transcribe\", \"output_dir\": \"tmp/\"}', NULL, NULL, 9, NULL, NULL, NULL, NULL);

-- groq ASR模型配置
delete from `ai_model_config` where id = 'ASR_GroqASR';
INSERT INTO `ai_model_config` VALUES ('ASR_GroqASR', 'ASR', 'GroqASR', 'Groq语音识别', 0, 1, '{\"type\": \"openai\", \"api_key\": \"\", \"base_url\": \"https://api.groq.com/openai/v1/audio/transcriptions\", \"model_name\": \"whisper-large-v3-turbo\", \"output_dir\": \"tmp/\"}', NULL, NULL, 10, NULL, NULL, NULL, NULL);


-- 更新OpenAI ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.openai.com/docs/api-reference/audio/createTranscription',
`remark` = 'OpenAI ASR配置说明：
1. 需要在OpenAI开放平台创建组织并获取api_key
2. 支持中、英、日、韩等多种语音识别，具体参考文档https://platform.openai.com/docs/guides/speech-to-text
3. 需要网络连接
4. 输出文件保存在tmp/目录
申请步骤：
**OpenAi ASR申请步骤：**
1.登录OpenAI Platform。https://auth.openai.com/log-in
2.创建api-key  https://platform.openai.com/settings/organization/api-keys
3.模型可以选择gpt-4o-transcribe或GPT-4o mini Transcribe
' WHERE `id` = 'ASR_OpenaiASR';

-- 更新Groq ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.groq.com/docs/speech-to-text',
`remark` = 'Groq ASR配置说明：
1.登录groq Console。https://console.groq.com/home
2.创建api-key  https://console.groq.com/keys
3.模型可以选择whisper-large-v3-turbo或whisper-large-v3（distil-whisper-large-v3-en仅支持英语转录）
' WHERE `id` = 'ASR_GroqASR';

-- -------------------------------------------------------------
-- 来源: 202507071130.sql
-- -------------------------------------------------------------
-- 添加阿里云流式ASR供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_AliyunStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_AliyunStreamASR', 'ASR', 'aliyun_stream', '阿里云语音识别(流式)', '[{"key":"appkey","label":"应用AppKey","type":"string"},{"key":"token","label":"临时Token","type":"string"},{"key":"access_key_id","label":"AccessKey ID","type":"string"},{"key":"access_key_secret","label":"AccessKey Secret","type":"string"},{"key":"host","label":"服务地址","type":"string"},{"key":"max_sentence_silence","label":"断句检测时间","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 6, 1, NOW(), 1, NOW());

-- 添加阿里云流式ASR模型配置
delete from `ai_model_config` where id = 'ASR_AliyunStreamASR';
INSERT INTO `ai_model_config` VALUES ('ASR_AliyunStreamASR', 'ASR', 'AliyunStreamASR', '阿里云语音识别(流式)', 0, 1, '{\"type\": \"aliyun_stream\", \"appkey\": \"\", \"token\": \"\", \"access_key_id\": \"\", \"access_key_secret\": \"\", \"host\": \"nls-gateway-cn-shanghai.aliyuncs.com\", \"max_sentence_silence\": 800, \"output_dir\": \"tmp/\"}', NULL, NULL, 8, NULL, NULL, NULL, NULL);

-- 更新阿里云流式ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云流式ASR配置说明：
1. 阿里云ASR和阿里云(流式)ASR的区别是：阿里云ASR是一次性识别，阿里云(流式)ASR是实时流式识别
2. 流式ASR具有更低的延迟和更好的实时性，适合语音交互场景
3. 需要在阿里云智能语音交互控制台创建应用并获取认证信息
4. 支持中文实时语音识别，支持标点符号预测和逆文本规范化
5. 需要网络连接，输出文件保存在tmp/目录
申请步骤：
1. 访问 https://nls-portal.console.aliyun.com/ 开通智能语音交互服务
2. 访问 https://nls-portal.console.aliyun.com/applist 创建项目并获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取临时token（或配置access_key_id和access_key_secret自动获取）
4. 如需动态token管理，建议配置access_key_id和access_key_secret
5. max_sentence_silence参数控制断句检测时间（毫秒），默认800ms
如需了解更多参数配置，请参考：https://help.aliyun.com/zh/isi/developer-reference/real-time-speech-recognition
' WHERE `id` = 'ASR_AliyunStreamASR';

-- -------------------------------------------------------------
-- 来源: 202507071530.sql
-- -------------------------------------------------------------
-- 添加阿里云流式TTS供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_AliyunStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_AliyunStreamTTS', 'TTS', 'aliyun_stream', '阿里云语音合成(流式)', '[{"key":"appkey","label":"应用AppKey","type":"string"},{"key":"token","label":"临时Token","type":"string"},{"key":"access_key_id","label":"AccessKey ID","type":"string"},{"key":"access_key_secret","label":"AccessKey Secret","type":"string"},{"key":"host","label":"服务地址","type":"string"},{"key":"voice","label":"默认音色","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key":"volume","label":"音量","type":"number"},{"key":"speech_rate","label":"语速","type":"number"},{"key":"pitch_rate","label":"音调","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 15, 1, NOW(), 1, NOW());

-- 添加阿里云流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_AliyunStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_AliyunStreamTTS', 'TTS', 'AliyunStreamTTS', '阿里云语音合成(流式)', 0, 1, '{\"type\": \"aliyun_stream\", \"appkey\": \"\", \"token\": \"\", \"access_key_id\": \"\", \"access_key_secret\": \"\", \"host\": \"nls-gateway-cn-beijing.aliyuncs.com\", \"voice\": \"longxiaochun\", \"format\": \"pcm\", \"sample_rate\": 16000, \"volume\": 50, \"speech_rate\": 0, \"pitch_rate\": 0, \"output_dir\": \"tmp/\"}', NULL, NULL, 18, NULL, NULL, NULL, NULL);

-- 更新阿里云流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://nls-portal.console.aliyun.com/',
`remark` = '阿里云流式TTS配置说明：
1. 阿里云TTS和阿里云(流式)TTS的区别是：阿里云TTS是一次性合成，阿里云(流式)TTS是实时流式合成
2. 流式TTS具有更低的延迟和更好的实时性，适合语音交互场景
3. 需要在阿里云智能语音交互控制台创建应用并获取认证信息
4. 支持CosyVoice大模型音色，音质更加自然
5. 支持实时调节音量、语速、音调等参数
申请步骤：
1. 访问 https://nls-portal.console.aliyun.com/ 开通智能语音交互服务
2. 访问 https://nls-portal.console.aliyun.com/applist 创建项目并获取appkey
3. 访问 https://nls-portal.console.aliyun.com/overview 获取临时token（或配置access_key_id和access_key_secret自动获取）
4. 如需动态token管理，建议配置access_key_id和access_key_secret
5. 可选择北京、上海等不同地域的服务器以优化延迟
6. voice参数支持CosyVoice大模型音色，如longxiaochun、longyueyue等
如需了解更多参数配置，请参考：https://help.aliyun.com/zh/isi/developer-reference/real-time-speech-synthesis
' WHERE `id` = 'TTS_AliyunStreamTTS';

-- 添加阿里云流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_AliyunStreamTTS';
-- 温柔女声系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0001', 'TTS_AliyunStreamTTS', '龙小淳-温柔姐姐', 'longxiaochun', '中文及中英文混合', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0002', 'TTS_AliyunStreamTTS', '龙小夏-温柔女声', 'longxiaoxia', '中文及中英文混合', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0003', 'TTS_AliyunStreamTTS', '龙玫-温柔女声', 'longmei', '中文及中英文混合', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0004', 'TTS_AliyunStreamTTS', '龙瑰-温柔女声', 'longgui', '中文及中英文混合', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
-- 御姐女声系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0005', 'TTS_AliyunStreamTTS', '龙玉-御姐女声', 'longyu', '中文及中英文混合', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0006', 'TTS_AliyunStreamTTS', '龙娇-御姐女声', 'longjiao', '中文及中英文混合', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
-- 男声系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0007', 'TTS_AliyunStreamTTS', '龙臣-译制片男声', 'longchen', '中文及中英文混合', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0008', 'TTS_AliyunStreamTTS', '龙修-青年男声', 'longxiu', '中文及中英文混合', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0009', 'TTS_AliyunStreamTTS', '龙橙-阳光男声', 'longcheng', '中文及中英文混合', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0010', 'TTS_AliyunStreamTTS', '龙哲-成熟男声', 'longzhe', '中文及中英文混合', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
-- 专业播报系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0011', 'TTS_AliyunStreamTTS', 'Bella2.0-新闻女声', 'loongbella', '中文及中英文混合', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0012', 'TTS_AliyunStreamTTS', 'Stella2.0-飒爽女声', 'loongstella', '中文及中英文混合', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0013', 'TTS_AliyunStreamTTS', '龙书-新闻男声', 'longshu', '中文及中英文混合', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0014', 'TTS_AliyunStreamTTS', '龙婧-严肃女声', 'longjing', '中文及中英文混合', NULL, NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
-- 特色音色系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0015', 'TTS_AliyunStreamTTS', '龙奇-活泼童声', 'longqi', '中文及中英文混合', NULL, NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0016', 'TTS_AliyunStreamTTS', '龙华-活泼女童', 'longhua', '中文及中英文混合', NULL, NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0017', 'TTS_AliyunStreamTTS', '龙无-无厘头男声', 'longwu', '中文及中英文混合', NULL, NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0018', 'TTS_AliyunStreamTTS', '龙大锤-幽默男声', 'longdachui', '中文及中英文混合', NULL, NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL);
-- 粤语系列
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0019', 'TTS_AliyunStreamTTS', '龙嘉怡-粤语女声', 'longjiayi', '粤语及粤英混合', NULL, NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliyunStreamTTS_0020', 'TTS_AliyunStreamTTS', '龙桃-粤语女声', 'longtao', '粤语及粤英混合', NULL, NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202507031602.sql
-- -------------------------------------------------------------
-- 添加声纹接口地址参数配置
delete from `sys_params` where id = 114;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (114, 'server.voice_print', 'null', 'string', 1, '声纹接口地址');

-- -------------------------------------------------------------
-- 来源: 202507041018.sql
-- -------------------------------------------------------------
DROP TABLE IF EXISTS ai_agent_voice_print;
create table ai_agent_voice_print (
  id varchar(32) NOT NULL COMMENT '声纹ID',
  agent_id varchar(32)  NOT NULL COMMENT '关联的智能体ID',
  source_name varchar(50)  NOT NULL COMMENT '声纹来源的人的姓名',
  introduce varchar(200) COMMENT '描述声纹来源的这个人',
  create_date DATETIME COMMENT '创建时间',
  creator bigint COMMENT '创建者',
  update_date DATETIME COMMENT '修改时间',
  updater bigint COMMENT '修改者',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体声纹表';

-- -------------------------------------------------------------
-- 来源: 202507081646.sql
-- -------------------------------------------------------------
-- 智能体声纹添加新字段
ALTER TABLE ai_agent_voice_print
    ADD COLUMN audio_id VARCHAR(32) NOT NULL COMMENT '音频ID';

-- -------------------------------------------------------------
-- 来源: 202508081701.sql
-- -------------------------------------------------------------
-- 添加Index-TTS-vLLM流式TTS供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_IndexStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_IndexStreamTTS', 'TTS', 'index_stream', 'Index-TTS-vLLM流式语音合成', '[{"key":"api_url","label":"API服务地址","type":"string"},{"key":"voice","label":"默认音色","type":"string"},{"key":"audio_format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 16, 1, NOW(), 1, NOW());

-- 添加Index-TTS-vLLM流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_IndexStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_IndexStreamTTS', 'TTS', 'IndexStreamTTS', 'Index-TTS-vLLM流式语音合成', 0, 1, '{\"type\": \"index_stream\", \"api_url\": \"http://127.0.0.1:11996/tts\", \"voice\": \"jay_klee\", \"audio_format\": \"pcm\", \"output_dir\": \"tmp/\"}', NULL, NULL, 19, NULL, NULL, NULL, NULL);

-- 更新Index-TTS-vLLM流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/Ksuriuri/index-tts-vllm',
`remark` = 'Index-TTS-vLLM流式TTS配置说明：
1. Index-TTS-vLLM是基于Index-TTS项目的vLLM推理服务，提供流式语音合成功能
2. 支持多种音色，音质自然，适合各种语音交互场景
3. 需要先部署Index-TTS-vLLM服务，然后配置API地址
4. 支持实时流式合成，具有较低的延迟
5. 支持自定义音色，可在项目assets文件夹下注册新音色
部署步骤：
1. 克隆项目：git clone https://github.com/Ksuriuri/index-tts-vllm.git
2. 安装依赖：pip install -r requirements.txt
3. 启动服务：python app.py
4. 服务默认运行在 http://127.0.0.1:11996
5. 如需其他音色，可到项目assets文件夹下注册
6. 支持多种音频格式：pcm、wav、mp3等
如需了解更多配置，请参考：https://github.com/Ksuriuri/index-tts-vllm/blob/master/README.md
' WHERE `id` = 'TTS_IndexStreamTTS';

-- 添加Index-TTS-vLLM流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_IndexStreamTTS';
-- 默认音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_IndexStreamTTS_0001', 'TTS_IndexStreamTTS', 'Jay Klee', 'jay_klee', '中文及中英文混合', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202508111734.sql
-- -------------------------------------------------------------
-- 更新HuoshanDoubleStreamTTS供应器增加语速，音调等配置
UPDATE `ai_model_provider`
SET fields = '[{"key": "ws_url", "type": "string", "label": "WebSocket地址"}, {"key": "appid", "type": "string", "label": "应用ID"}, {"key": "access_token", "type": "string", "label": "访问令牌"}, {"key": "resource_id", "type": "string", "label": "资源ID"}, {"key": "speaker", "type": "string", "label": "默认音色"}, {"key": "speech_rate", "type": "number", "label": "语速(-50~100)"}, {"key": "loudness_rate", "type": "number", "label": "音量(-50~100)"}, {"key": "pitch", "type": "number", "label": "音高(-12~12)"}]'
WHERE id = 'SYSTEM_TTS_HSDSTTS';

UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 语速：-50~100，可不填，正常默认值0，可填-50~100
7. 音量：-50~100，可不填，正常默认值0，可填-50~100
8. 音高：-12~12，可不填，正常默认值0，可填-12~12
9. 填入配置文件中' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- -------------------------------------------------------------
-- 来源: 202508131557.sql
-- -------------------------------------------------------------
-- 添加 paddle_speech 流式 TTS 供应器
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_TTS_PaddleSpeechTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) 
VALUES ('SYSTEM_TTS_PaddleSpeechTTS', 'TTS', 'paddle_speech', 'PaddleSpeechTTS', 
'[{"key":"protocol","label":"协议类型","type":"string","options":["websocket","http"]},{"key":"url","label":"服务地址","type":"string"},{"key":"spk_id","label":"音色","type":"int"},{"key":"sample_rate","label":"采样率","type":"float"},{"key":"speed","label":"语速","type":"float"},{"key":"volume","label":"音量","type":"float"},{"key":"save_path","label":"保存路径","type":"string"}]', 
17, 1, NOW(), 1, NOW());

-- 添加 paddle_speech 流式 TTS 模型配置
DELETE FROM `ai_model_config` WHERE id = 'TTS_PaddleSpeechTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_PaddleSpeechTTS', 'TTS', 'PaddleSpeechTTS', 'PaddleSpeechTTS', 0, 1, 
'{"type": "paddle_speech", "protocol": "websocket", "url": "ws://127.0.0.1:8092/paddlespeech/tts/streaming", "spk_id": "0", "sample_rate": 24000, "speed": 1.0, "volume": 1.0, "save_path": "./streaming_tts.wav"}', 
NULL, NULL, 20, NULL, NULL, NULL, NULL);

-- 更新 PaddleSpeechTTS 配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/PaddlePaddle/PaddleSpeech',
`remark` = 'PaddleSpeechTTS 配置说明：
1. PaddleSpeech 是百度飞桨开源的语音合成工具，支持本地离线部署和模型训练。paddlepaddle百度飞浆框架地址：https://www.paddlepaddle.org.cn/
2. 支持 WebSocket 和 HTTP 协议，默认使用 WebSocket 进行流式传输（参考部署文档：https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/paddlespeech-deploy.md）。
3. 使用前要在本地部署 paddlespeech 服务，服务默认运行在 ws://127.0.0.1:8092/paddlespeech/tts/streaming
4. 支持自定义发音人、语速、音量和采样率。
' WHERE `id` = 'TTS_PaddleSpeechTTS';

-- 删除旧音色并添加默认音色
DELETE FROM `ai_tts_voice` WHERE tts_model_id = 'TTS_PaddleSpeechTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_PaddleSpeechTTS_0000', 'TTS_PaddleSpeechTTS', '默认', '0', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202508271113.sql
-- -------------------------------------------------------------
-- VOSK ASR模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_VoskASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_VoskASR', 'ASR', 'vosk', 'VOSK离线语音识别', '[{"key": "model_path", "type": "string", "label": "模型路径"}, {"key": "output_dir", "type": "string", "label": "输出目录"}]', 11, 1, NOW(), 1, NOW());

-- VOSK ASR模型配置
delete from `ai_model_config` where id = 'ASR_VoskASR';
INSERT INTO `ai_model_config` VALUES ('ASR_VoskASR', 'ASR', 'VoskASR', 'VOSK离线语音识别', 0, 1, '{\"type\": \"vosk\", \"model_path\": \"\", \"output_dir\": \"tmp/\"}', NULL, NULL, 11, NULL, NULL, NULL, NULL);

-- 更新VOSK ASR配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://alphacephei.com/vosk/',
`remark` = 'VOSK ASR配置说明：
1. VOSK是一个离线语音识别库，支持多种语言
2. 需要先下载模型文件：https://alphacephei.com/vosk/models
3. 中文模型推荐使用vosk-model-small-cn-0.22或vosk-model-cn-0.22
4. 完全离线运行，无需网络连接
5. 输出文件保存在tmp/目录
使用步骤：
1. 访问 https://alphacephei.com/vosk/models 下载中文模型
2. 解压模型文件到项目目录下的models/vosk/文件夹
3. 在配置中指定正确的模型路径
4. 注意：VOSK中文模型输出不带标点符号，词与词之间会有空格
' WHERE `id` = 'ASR_VoskASR';

-- -------------------------------------------------------------
-- 来源: 202509051745.sql
-- -------------------------------------------------------------
-- 添加 MinimaxHTTPStream 流式 TTS 供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_MinimaxStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_MinimaxStreamTTS', 'TTS', 'minimax_httpstream', 'Minimax流式语音合成', '[{"key":"group_id","label":"组ID","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice_id","label":"音色ID","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice_setting","label":"音色设置","type":"dict","dict_name":"voice_setting"},{"key":"pronunciation_dict","label":"发音字典","type":"dict","dict_name":"pronunciation_dict"},{"key":"audio_setting","label":"音频设置","type":"dict","dict_name":"audio_setting"},{"key":"timber_weights","label":"音色权重","type":"string"}]', 18, 1, NOW(), 1, NOW());

-- 添加Minimax流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_MinimaxStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_MinimaxStreamTTS', 'TTS', 'MinimaxStreamTTS', 'Minimax流式语音合成', 0, 1, '{"type": "minimax_httpstream", "group_id": "", "api_key": "", "model": "speech-01-turbo", "voice_id": "female-shaonv", "output_dir": "tmp/", "voice_setting": {"speed": 1, "vol": 1, "pitch": 0, "emotion": "happy"}, "pronunciation_dict": {"tone": ["处理/(chu3)(li3)", "危险/dangerous"]}, "audio_setting": {"sample_rate": 24000, "bitrate": 128000, "format": "pcm", "channel": 1}}', NULL, NULL, 21, NULL, NULL, NULL, NULL);

-- 更新Minimax流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://platform.minimaxi.com/',
`remark` = 'Minimax流式TTS配置说明：
1. 需要先申请Minimax API Key
2. 需要填写Group ID
3. 支持多种音色设置和音频参数调整
4. 支持实时流式合成，具有较低的延迟
5. 支持自定义发音字典和音色权重
6. 隐藏参数配置：声音设定(voice_setting)、发音字典(pronunciation_dict)、音色权重(timber_weights)
   - 语速(speed): 范围[0.5,2]，默认1.0，取值越大语速越快
   - 音量(vol): 范围(0,10]，默认1.0，取值越大音量越高
   - 音调(pitch): 范围[-12,12]，默认0，取值需为整数
   - 情绪(emotion): 控制合成语音的情绪，支持7种值：["happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm"]，该参数仅对 speech-2.5-hd-preview、speech-2.5-turbo-preview、speech-02-hd、speech-02-turbo、speech-01-turbo、speech-01-hd 生效
   - timbre_weights与voice_id二选一必填
   - voice_id(请求的音色id，须和weight参数同步填写)
   - weight(权重，最多支持4种音色混合。范围[1,100])
' WHERE `id` = 'TTS_MinimaxStreamTTS';

-- 添加Minimax流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_MinimaxStreamTTS';

-- 默认音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0001', 'TTS_MinimaxStreamTTS', '少女音', 'female-shaonv', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0002', 'TTS_MinimaxStreamTTS', '成熟女声', 'female-chengshu', '中文', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0003', 'TTS_MinimaxStreamTTS', '霸道少爷', 'badao_shaoye', '中文', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0004', 'TTS_MinimaxStreamTTS', '病娇弟弟', 'bingjiao_didi', '中文', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0005', 'TTS_MinimaxStreamTTS', '纯真学弟', 'chunzhen_xuedi', '中文', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0006', 'TTS_MinimaxStreamTTS', '冷淡学长', 'lengdan_xiongzhang', '中文', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0007', 'TTS_MinimaxStreamTTS', '甜美小玲', 'tianxin_xiaoling', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0008', 'TTS_MinimaxStreamTTS', '俏皮萌妹', 'qiaopi_mengmei', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0009', 'TTS_MinimaxStreamTTS', '妩媚御姐', 'wumei_yujie', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0010', 'TTS_MinimaxStreamTTS', '嗲嗲学妹', 'diadia_xuemei', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0011', 'TTS_MinimaxStreamTTS', '淡雅学姐', 'danya_xuejie', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0012', 'TTS_MinimaxStreamTTS', 'Santa Claus', 'Santa_Claus', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0013', 'TTS_MinimaxStreamTTS', 'Grinch', 'Grinch', '中文', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202509081140.sql
-- -------------------------------------------------------------
-- 添加声纹识别相似度阈值参数配置
delete from `sys_params` where id = 115;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (115, 'server.voiceprint_similarity_threshold', '0.4', 'string', 1, '声纹识别相似度阈值，范围0.0-1.0，默认0.4，数值越高越严格');

-- -------------------------------------------------------------
-- 来源: 202509091042.sql
-- -------------------------------------------------------------
-- 删除非流式MiniMax TTS配置，保留流式版本

-- 删除旧的非流式MiniMax TTS模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'TTS_MinimaxTTS';

-- 删除旧的非流式MiniMax TTS供应器配置  
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_TTS_minimax';

-- 删除旧的非流式MiniMax TTS音色配置
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_MinimaxTTS';

-- -------------------------------------------------------------
-- 来源: 202509091633.sql
-- -------------------------------------------------------------
-- 添加通义千问Qwen3-ASR-Flash语音识别服务配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_Qwen3Flash';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_Qwen3Flash', 'ASR', 'qwen3_asr_flash', 'Qwen3-ASR-Flash语音识别', '[{"key":"api_key","label":"API密钥","type":"password"},{"key":"base_url","label":"服务地址","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 17, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'ASR_Qwen3Flash';
INSERT INTO `ai_model_config` VALUES ('ASR_Qwen3Flash', 'ASR', 'Qwen3-ASR-Flash', '通义千问语音识别服务', 0, 1, '{"type": "qwen3_asr_flash", "api_key": "", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen3-asr-flash", "output_dir": "tmp/", "enable_lid": true, "enable_itn": true}', 'https://help.aliyun.com/zh/bailian/', '支持多语言识别、歌唱识别、噪声拒识功能', 20, NULL, NULL, NULL, NULL);

-- 更新Qwen3-ASR-Flash模型配置的说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1&tab=doc#/doc/?type=model&url=2979031',
`remark` = '通义千问Qwen3-ASR-Flash配置说明：
1. 登录阿里云百炼平台https://bailian.console.aliyun.com/
2. 创建API-KEY  https://bailian.console.aliyun.com/#/api-key
3.Qwen3-ASR-Flash基于通义千问多模态基座，支持多语言识别、歌唱识别、噪声拒识等功能
' WHERE `id` = 'ASR_Qwen3Flash';

-- -------------------------------------------------------------
-- 来源: 202509080922.sql
-- -------------------------------------------------------------
delete from `sys_params` where param_code = 'server.mqtt_gateway';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (116, 'server.mqtt_gateway', 'null', 'string', 1, 'mqtt gateway 配置');

delete from `sys_params` where param_code = 'server.mqtt_signature_key';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (117, 'server.mqtt_signature_key', 'null', 'string', 1, 'mqtt 密钥 配置');

delete from `sys_params` where param_code = 'server.udp_gateway';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (118, 'server.udp_gateway', 'null', 'string', 1, 'udp gateway 配置');

-- -------------------------------------------------------------
-- 来源: 202509161610.sql
-- -------------------------------------------------------------
delete from `sys_params` where param_code = 'server.mqtt_manager_api';
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark)
VALUES (119, 'server.mqtt_manager_api', 'null', 'string', 1, 'MQTT网关管理API的地址');

-- -------------------------------------------------------------
-- 来源: 202509161701.sql
-- -------------------------------------------------------------
-- 添加阿里百炼流式TTS 供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_AliBLStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_AliBLStreamTTS', 'TTS', 'alibl_stream', '阿里百炼流式语音合成', '[{"key":"api_key","label":"API密钥","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"model","label":"模型","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key": "volume", "type": "number", "label": "音量"},{"key": "rate", "type": "number", "label": "语速"},{"key": "pitch", "type": "number", "label": "音调"}]', 19, 1, NOW(), 1, NOW());

-- 添加阿里百炼流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_AliBLStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_AliBLStreamTTS', 'TTS', 'AliBLStreamTTS', '阿里百炼流式语音合成', 0, 1, '{\"type\": \"alibl_stream\", \"appkey\": \"\", \"output_dir\": \"tmp/\", \"model\": \"cosyvoice-v2\", \"voice\": \"longcheng_v2\", \"format\": \"pcm\", \"sample_rate\": 24000, \"volume\": 50, \"rate\": 1, \"pitch\": 1}', NULL, NULL, 22, NULL, NULL, NULL, NULL);

-- 更新阿里百炼流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1#/api-key',
`remark` = '阿里百炼流式TTS说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key 创建项目并获取appkey
2. 支持实时流式合成，具有较低的延迟
3. 支持多种音色设置和音频参数调整
4. 支持CosyVoice-V3大模型音色，价格实惠(0.4元/万字符)
5. 支持实时调节音量、语速、音调等参数
6. 如果需要使用CosyVoice-V3模型和一些限制类型的音色，需要联系阿里百炼客服申请
' WHERE `id` = 'TTS_AliBLStreamTTS';

-- 添加阿里百炼流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_AliBLStreamTTS';

-- 语音助手
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0001', 'TTS_AliBLStreamTTS', '龙小淳-知性积极女', 'longxiaochun_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0002', 'TTS_AliBLStreamTTS', '龙小夏-沉稳权威女', 'longxiaoxia_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);

-- 直播带货
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0003', 'TTS_AliBLStreamTTS', '龙安燃-活泼质感女', 'longanran', '中文及中英文混合', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0004', 'TTS_AliBLStreamTTS', '龙安宣-经典直播女', 'longanxuan', '中文及中英文混合', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);

-- 社交陪伴
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0005', 'TTS_AliBLStreamTTS', '龙寒-温暖痴情男', 'longhan_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0006', 'TTS_AliBLStreamTTS', '龙颜-温暖春风女', 'longyan_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0007', 'TTS_AliBLStreamTTS', '龙菲菲-甜美矫情女', 'longfeifei_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);

-- 方言
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0008', 'TTS_AliBLStreamTTS', '龙老铁-东北直率男', 'longlaotie_v2', '中文(东北)及中英文混合', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0009', 'TTS_AliBLStreamTTS', '龙嘉怡-知性粤语女', 'longjiayi_v2', '中文(粤语)及中英文混合', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);

-- 童声
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0010', 'TTS_AliBLStreamTTS', '龙杰力豆-阳光顽皮男', 'longjielidou_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0011', 'TTS_AliBLStreamTTS', '龙铃-稚气呆板女', 'longling_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);

-- 诗歌朗诵
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0012', 'TTS_AliBLStreamTTS', '李白-古代诗仙男', 'libai_v2', '中文及中英文混合', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);

-- 出海营销
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0013', 'TTS_AliBLStreamTTS', 'loongeva-知性英文女', 'loongeva_v2', '英式英文', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0014', 'TTS_AliBLStreamTTS', 'loongbrian-沉稳英文男', 'loongbrian_v2', '英式英文', NULL, NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0015', 'TTS_AliBLStreamTTS', 'loongkyong-韩语女', 'loongkyong_v2', '韩语', NULL, NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0016', 'TTS_AliBLStreamTTS', 'loongtomoka-日语女', 'loongtomoka_v2', '日语', NULL, NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_AliBLStreamTTS_0017', 'TTS_AliBLStreamTTS', 'loongtomoya-日语男', 'loongtomoya_v2', '日语', NULL, NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202509221530.sql
-- -------------------------------------------------------------
-- 添加SM2国密算法密钥参数
-- 用于服务器端SM2加密解密功能

-- 添加SM2密钥参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES 
(120, 'server.public_key', '', 'string', 1, '服务器SM2公钥'),
(121, 'server.private_key', '', 'string', 1, '服务器SM2私钥');

-- -------------------------------------------------------------
-- 来源: 202509191545.sql
-- -------------------------------------------------------------
-- 添加讯飞流式TTS供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_XunFeiStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_XunFeiStreamTTS', 'TTS', 'xunfei_stream', '讯飞流式语音合成', '[{"key":"app_id","label":"APP_ID","type":"string"},{"key":"api_secret","label":"API_Secret","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice","label":"音色","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key": "volume", "type": "number", "label": "音量"},{"key": "speed", "type": "number", "label": "语速"},{"key": "pitch", "type": "number", "label": "音调"},{"key": "oral_level", "type": "number", "label": "口语化等级"},{"key": "spark_assist", "type": "number", "label": "是否口语化"},{"key": "stop_split", "type": "number", "label": "服务端拆句"},{"key": "remain", "type": "number", "label": "保留书面语"}]', 20, 1, NOW(), 1, NOW());

-- 添加讯飞流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_XunFeiStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_XunFeiStreamTTS', 'TTS', 'XunFeiStreamTTS', '讯飞流式语音合成', 0, 1, '{\"type\": \"xunfei_stream\", \"app_id\": \"\", \"api_secret\": \"\", \"api_key\": \"\", \"output_dir\": \"tmp/\", \"voice\": \"x5_lingxiaoxuan_flow\", \"format\": \"raw\", \"sample_rate\": 24000, \"volume\": 50, \"speed\": 50, \"pitch\": 50, \"oral_level\": \"mid\", \"spark_assist\": 1, \"stop_split\": 0, \"remain\": 0}', NULL, NULL, 23, NULL, NULL, NULL, NULL);

-- 更新讯飞流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.xfyun.cn/app/myapp',
`remark` = '讯飞流式TTS说明：
1. 登录讯飞语音技术平台 https://console.xfyun.cn/app/myapp 创建相关应用
2. 选择需要的服务获取api相关配置 https://console.xfyun.cn/services/uts
3. 为需要使用的应用(APPID)购买相关服务 例如：超拟人合成 https://console.xfyun.cn/services/uts
5. 支持实时双流式通信，具有较低的延迟
6. 支持口语化设置和音频参数调整 注意：V5音色不支持相关口语化配置
7. 支持实时调节音量、语速、音调等参数
' WHERE `id` = 'TTS_XunFeiStreamTTS';

-- 添加讯飞流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_XunFeiStreamTTS';

-- 基础角色
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0001', 'TTS_XunFeiStreamTTS', '聆小璇', 'x5_lingxiaoxuan_flow', '中文', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0002', 'TTS_XunFeiStreamTTS', '聆飞逸', 'x5_lingfeiyi_flow', '中文', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0003', 'TTS_XunFeiStreamTTS', '聆小玥', 'x5_lingxiaoyue_flow', '中文', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0004', 'TTS_XunFeiStreamTTS', '聆玉昭', 'x5_lingyuzhao_flow', '中文', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0005', 'TTS_XunFeiStreamTTS', '聆玉言', 'x5_lingyuyan_flow', '中文', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);

-- 需要添加对应的角色音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0006', 'TTS_XunFeiStreamTTS', '聆飞哲', 'x4_lingfeizhe_oral', '中文', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0007', 'TTS_XunFeiStreamTTS', '聆小璃', 'x4_lingxiaoli_oral', '中文', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0008', 'TTS_XunFeiStreamTTS', '聆小糖', 'x5_lingxiaotang_flow', '中文', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0009', 'TTS_XunFeiStreamTTS', '聆小琪', 'x4_lingxiaoqi_oral', '中文', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0010', 'TTS_XunFeiStreamTTS', '聆佑佑-童年女声', 'x4_lingyouyou_oral', '中文', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0011', 'TTS_XunFeiStreamTTS', '子津', 'x4_zijin_oral', '天津话', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0012', 'TTS_XunFeiStreamTTS', '子阳', 'x4_ziyang_oral', '东北话', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0013', 'TTS_XunFeiStreamTTS', 'Grant', 'x5_EnUs_Grant_flow', '英文', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_XunFeiStreamTTS_0014', 'TTS_XunFeiStreamTTS', 'Lila', 'x5_EnUs_Lila_flow', '英文', NULL, NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202509220926.sql
-- -------------------------------------------------------------
-- 添加讯飞流式语音识别服务配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_XunfeiStream';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_XunfeiStream', 'ASR', 'xunfei_stream', '讯飞流式语音识别', '[{"key":"app_id","label":"应用ID","type":"string"},{"key":"api_key","label":"API_KEY","type":"password"},{"key":"api_secret","label":"API_SECRET","type":"password"},{"key":"domain","label":"识别领域","type":"string"},{"key":"language","label":"识别语言","type":"string"},{"key":"accent","label":"方言","type":"string"},{"key":"dwa","label":"动态修正","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 18, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'ASR_XunfeiStream';
INSERT INTO `ai_model_config` VALUES ('ASR_XunfeiStream', 'ASR', '讯飞流式语音识别', '讯飞流式语音识别服务', 0, 1, '{"type": "xunfei_stream", "app_id": "", "api_key": "", "api_secret": "", "domain": "slm", "language": "zh_cn", "accent": "mandarin", "dwa": "wpgs", "output_dir": "tmp/"}', 'https://www.xfyun.cn/doc/spark/spark_zh_iat.html', '支持实时流式语音识别，适用于中文普通话及多种方言识别', 21, NULL, NULL, NULL, NULL);

-- 更新讯飞流式语音识别模型配置的说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.xfyun.cn/doc/spark/spark_zh_iat.html',
`remark` = '讯飞流式语音识别配置说明：
1. 登录讯飞开放平台 https://www.xfyun.cn/
2. 创建语音识别应用获取APPID、APISecret、APIKey
3. 参数说明：
   - app_id: 应用ID，在讯飞开放平台创建应用后获得
   - api_key: API密钥，用于接口鉴权
   - api_secret: API密钥，用于生成签名
   - domain: 识别领域，默认slm（智能化语音转写）
   - language: 识别语言，默认zh_cn（中文）
   - accent: 方言类型，默认mandarin（普通话），支持cantonese（粤语）等
   - dwa: 动态修正，默认wpgs（开启动态修正）
   - output_dir: 音频文件输出目录，默认tmp/
4. 支持实时流式识别，适用于实时语音交互场景
5. 支持多种方言和语言识别
' WHERE `id` = 'ASR_XunfeiStream';

-- -------------------------------------------------------------
-- 来源: 202509220958.sql
-- -------------------------------------------------------------
delete from `ai_model_config` where id = 'LLM_XunfeiSparkLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_XunfeiSparkLLM', 'LLM', '讯飞星火认知大模型', '讯飞星火认知大模型', 0, 1, '{"type": "openai", "model_name": "generalv3.5", "base_url": "https://spark-api-open.xf-yun.com/v1", "api_password": "你的api_password", "temperature": 0.5, "max_tokens": 2048, "top_p": 1.0, "frequency_penalty": 0.0}', 'https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html', '讯飞星火认知大模型，支持多轮对话、文本生成等功能', 14, NULL, NULL, NULL, NULL);

-- 更新讯飞星火认知大模型配置的说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html',
`remark` = '讯飞星火认知大模型配置说明：
1. 登录讯飞开放平台 https://www.xfyun.cn/，每一个模型对应每一个api_password,更改模型时需要查看对应模型的api_password
2. 创建星火认知大模型应用获取API Password
3. 参数说明：
   - api_password: API Password，在讯飞开放平台创建应用后获得
   - model_name: 模型名称，支持generalv3.5、generalv3等版本
   - base_url: API地址，默认https://spark-api-open.xf-yun.com/v1
   - temperature: 温度参数，控制生成随机性，范围0-1，默认0.5
   - max_tokens: 最大输出token数，默认2048
   - top_p: 核心采样参数，控制词汇多样性，默认1.0
   - frequency_penalty: 频率惩罚，降低重复内容，默认0.0
4. 每一个模型对应每一个api_password,更改模型时需要查看对应模型的api_password。
' WHERE `id` = 'LLM_XunfeiSparkLLM';

-- -------------------------------------------------------------
-- 来源: 202510071522.sql
-- -------------------------------------------------------------
-- 声音克隆表
DROP TABLE IF EXISTS `ai_voice_clone`;
CREATE TABLE `ai_voice_clone` (
    `id` VARCHAR(32) NOT NULL COMMENT '唯一标识',
    `name` VARCHAR(64) COMMENT '声音名称',
    `model_id` VARCHAR(32) COMMENT '模型id',
    `voice_id` VARCHAR(32) COMMENT '声音id',
    `user_id` BIGINT COMMENT '用户 ID（关联用户表）',
    `voice` LONGBLOB COMMENT '声音',
    `train_status` TINYINT(1) DEFAULT 0 COMMENT '训练状态：0待训练 1训练中 2训练成功 3训练失败',
    `train_error` VARCHAR(255) COMMENT '训练错误原因',
    `creator` BIGINT COMMENT '创建者 ID',
    `create_date` DATETIME COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX idx_ai_voice_clone_user_id_model_id_train_status (model_id,user_id, train_status),
    INDEX idx_ai_voice_clone_voice_id (voice_id),
    INDEX idx_ai_voice_clone_user_id (user_id),
    INDEX idx_ai_voice_clone_model_id_voice_id (model_id, voice_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='声音克隆表';

-- -------------------------------------------------------------
-- 来源: 202510191042.sql
-- -------------------------------------------------------------
UPDATE `ai_model_config` SET model_code = 'XunfeiSparkLLM' WHERE id = 'LLM_XunfeiSparkLLM';
UPDATE `ai_model_config` SET model_code = 'XunfeiStreamASR' WHERE id = 'ASR_XunfeiStream';

-- -------------------------------------------------------------
-- 来源: 202510250956.sql
-- -------------------------------------------------------------
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

-- -------------------------------------------------------------
-- 来源: 202510251150.sql
-- -------------------------------------------------------------
-- 知识库表
DROP TABLE IF EXISTS `ai_rag_dataset`;
CREATE TABLE `ai_rag_dataset` (
    `id` VARCHAR(32) NOT NULL COMMENT '唯一标识',
    `dataset_id` VARCHAR(64) NOT NULL COMMENT '知识库ID',
    `rag_model_id` VARCHAR(64) COMMENT 'RAG模型配置ID',
    `name` VARCHAR(100) NOT NULL COMMENT '知识库名称',
    `description` TEXT COMMENT '知识库描述',
    `status` TINYINT(1) DEFAULT 1 COMMENT '状态：0停用 1启用',
    `creator` BIGINT COMMENT '创建者',
    `created_at` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `updated_at` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_dataset_id` (`dataset_id`),
    INDEX `idx_ai_rag_dataset_status` (`status`),
    INDEX `idx_ai_rag_dataset_creator` (`creator`),
    INDEX `idx_ai_rag_dataset_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';

-- -------------------------------------------------------------
-- 来源: 202511131023.sql
-- -------------------------------------------------------------
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/infiniflow/ragflow/blob/main/README_zh.md',
`remark` = '详细部署教程参考：https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/ragflow-integration.md
部署成功，注冊登录后，点击右上角头像，获得RAGFlow的API KEY和API服务器地址。使用RAGFlow前请在Model Provider中添加模型和设置默认模型。' WHERE `id` = 'RAG_RAGFlow';

update `ai_model_config` set `model_name` = '外挂的大模型意图识别' where `id` = 'Intent_intent_llm';
update `ai_model_config` set `model_name` = '大模型自主函数调用' where `id` = 'Intent_function_call';
update `ai_model_config` set `model_name` = '百炼智能体应用' where `id` = 'LLM_AliAppLLM';

update `ai_model_provider` set `name` = '外挂的大模型意图识别' , `fields` =  '[{"key":"llm","label":"引用的LLM模型","type":"string"}]' where  id = 'SYSTEM_Intent_intent_llm';
update `ai_model_provider` set `name` = '大模型自主函数调用' where  id = 'SYSTEM_Intent_function_call';

UPDATE ai_model_config set model_name = 'Linkerai(流式)' where id = 'TTS_LinkeraiTTS';
UPDATE ai_model_config set model_name = '火山引擎(流式)' where id = 'TTS_HuoshanDoubleStreamTTS';
UPDATE ai_model_config set model_name = '阿里百炼(流式)' where id = 'TTS_AliBLStreamTTS';
UPDATE ai_model_config set model_name = '科大讯飞(流式)' where id = 'TTS_XunFeiStreamTTS';
UPDATE ai_model_config set model_name = 'Minimax(流式)' where id = 'TTS_MinimaxStreamTTS';
UPDATE ai_model_config set model_name = '阿里云(流式)' where id = 'TTS_AliyunStreamTTS';
UPDATE ai_model_config set model_name = 'PaddleSpeech(流式)' where id = 'TTS_PaddleSpeechTTS';
UPDATE ai_model_config set model_name = 'IndexTTS(流式)' where id = 'TTS_IndexStreamTTS';

update ai_model_config SET sort = 2 where id = 'TTS_LinkeraiTTS';
update ai_model_config SET sort = 3 where id = 'TTS_HuoshanDoubleStreamTTS';
update ai_model_config SET sort = 4 where id = 'TTS_AliBLStreamTTS';
update ai_model_config SET sort = 5 where id = 'TTS_XunFeiStreamTTS';
update ai_model_config SET sort = 6 where id = 'TTS_MinimaxStreamTTS';
update ai_model_config SET sort = 7 where id = 'TTS_AliyunStreamTTS';
update ai_model_config SET sort = 8 where id = 'TTS_IndexStreamTTS';
update ai_model_config SET sort = 9 where id = 'TTS_PaddleSpeechTTS';
update ai_model_config SET sort = 10 where id = 'TTS_DoubaoTTS';
update ai_model_config SET sort = 11 where id = 'TTS_TencentTTS';
update ai_model_config SET sort = 12 where id = 'TTS_AliyunTTS';
update ai_model_config SET sort = 13 where id = 'TTS_OpenAITTS';
update ai_model_config SET sort = 14 where id = 'TTS_CosyVoiceSiliconflow';
update ai_model_config SET sort = 15 where id = 'TTS_CozeCnTTS';
update ai_model_config SET sort = 16 where id = 'TTS_FishSpeech';
update ai_model_config SET sort = 17 where id = 'TTS_GPT_SOVITS_V3';
update ai_model_config SET sort = 18 where id = 'TTS_GPT_SOVITS_V2';
update ai_model_config SET sort = 19 where id = 'TTS_TTS302AI';
update ai_model_config SET sort = 20 where id = 'TTS_GizwitsTTS';
update ai_model_config SET sort = 21 where id = 'TTS_VolcesAiGatewayTTS';
update ai_model_config SET sort = 22 where id = 'TTS_ACGNTTS';
update ai_model_config SET sort = 23 where id = 'TTS_CustomTTS';

UPDATE ai_model_config set model_name = '讯飞语音识别(流式)' where id = 'ASR_XunfeiStream';
UPDATE ai_model_config set model_name = 'Qwen3Flash语音识别' where id = 'ASR_Qwen3Flash';

update ai_model_config SET sort = 2 where id = 'ASR_FunASRServer';
update ai_model_config SET sort = 3 where id = 'ASR_XunfeiStream';
update ai_model_config SET sort = 4 where id = 'ASR_AliyunStreamASR';
update ai_model_config SET sort = 5 where id = 'ASR_DoubaoStreamASR';
update ai_model_config SET sort = 6 where id = 'ASR_TencentASR';
update ai_model_config SET sort = 7 where id = 'ASR_BaiduASR';
update ai_model_config SET sort = 8 where id = 'ASR_DoubaoASR';
update ai_model_config SET sort = 9 where id = 'ASR_AliyunASR';
update ai_model_config SET sort = 10 where id = 'ASR_SherpaASR';
update ai_model_config SET sort = 11 where id = 'ASR_OpenaiASR';
update ai_model_config SET sort = 12 where id = 'ASR_GroqASR';
update ai_model_config SET sort = 13 where id = 'ASR_VoskASR';
update ai_model_config SET sort = 14 where id = 'ASR_Qwen3Flash';

UPDATE ai_model_config SET config_json='{\"type\": \"openai\", \"base_url\": \"https://ark.cn-beijing.volces.com/api/v3\", \"model_name\": \"doubao-1-5-pro-32k-250115\", \"api_key\": \"你的api_key\"}' where id = 'LLM_DoubaoLLM' AND config_json LIKE '%你的api_key"%';

-- -------------------------------------------------------------
-- 来源: 202511221450.sql
-- -------------------------------------------------------------
-- 更新HuoshanDoubleStreamTTS供应器配置，增加开启链接复用选项
UPDATE `ai_model_provider`
SET fields = '[{"key": "ws_url", "type": "string", "label": "WebSocket地址"}, {"key": "appid", "type": "string", "label": "应用ID"}, {"key": "access_token", "type": "string", "label": "访问令牌"}, {"key": "resource_id", "type": "string", "label": "资源ID"}, {"key": "speaker", "type": "string", "label": "默认音色"}, {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true}, {"key": "speech_rate", "type": "number", "label": "语速(-50~100)"}, {"key": "loudness_rate", "type": "number", "label": "音量(-50~100)"}, {"key": "pitch", "type": "number", "label": "音高(-12~12)"}]'
WHERE id = 'SYSTEM_TTS_HSDSTTS';

UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 链接复用：开启WebSocket连接复用，默认true减少链接损耗（注意：复用后设备处于聆听状态时空闲链接会占并发数）
7. 语速：-50~100，可不填，正常默认值0，可填-50~100
8. 音量：-50~100，可不填，正常默认值0，可填-50~100
9. 音高：-12~12，可不填，正常默认值0，可填-12~12
10. 填入配置文件中' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- -------------------------------------------------------------
-- 来源: 202512031517.sql
-- -------------------------------------------------------------
-- 添加系统功能菜单配置参数
delete from `sys_params` where param_code = 'system-web.menu';

-- 添加系统功能菜单配置参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES 
(600, 'system-web.menu', '{"features":{"voiceprintRecognition":{"name":"feature.voiceprintRecognition.name","enabled":false,"description":"feature.voiceprintRecognition.description"},"voiceClone":{"name":"feature.voiceClone.name","enabled":false,"description":"feature.voiceClone.description"},"knowledgeBase":{"name":"feature.knowledgeBase.name","enabled":false,"description":"feature.knowledgeBase.description"},"mcpAccessPoint":{"name":"feature.mcpAccessPoint.name","enabled":false,"description":"feature.mcpAccessPoint.description"},"vad":{"name":"feature.vad.name","enabled":true,"description":"feature.vad.description"},"asr":{"name":"feature.asr.name","enabled":true,"description":"feature.asr.description"}},"groups":{"featureManagement":["voiceprintRecognition","voiceClone","knowledgeBase","mcpAccessPoint"],"voiceManagement":["vad","asr"]}}', 'json', 1, '系统功能菜单配置');

-- -------------------------------------------------------------
-- 来源: 202512041515.sql
-- -------------------------------------------------------------

CREATE TABLE ai_agent_context_provider (
    id VARCHAR(32) NOT NULL COMMENT '主键',
    agent_id VARCHAR(32) NOT NULL COMMENT '智能体ID',
    context_providers JSON COMMENT '上下文源配置',
    creator BIGINT COMMENT '创建者',
    created_at DATETIME COMMENT '创建时间',
    updater BIGINT COMMENT '更新者',
    updated_at DATETIME COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_agent_id (agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体上下文源配置表';

-- -------------------------------------------------------------
-- 来源: 202512131453.sql
-- -------------------------------------------------------------
-- 删除server模块是否开启token认证参数
delete from `sys_params` where param_code = 'server.auth.enabled';

-- 添加server模块是否开启token认证参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES 
(122, 'server.auth.enabled', 'true', 'boolean', 1, 'server模块是否开启token认证');

-- -------------------------------------------------------------
-- 来源: 202512161529.sql
-- -------------------------------------------------------------
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (311, 'enable_websocket_ping', 'false', 'boolean', 1, '是否启用WebSocket心跳保活机制');

-- -------------------------------------------------------------
-- 来源: 202512192245.sql
-- -------------------------------------------------------------
-- 为智能体聊天历史记录添加音频ID索引
ALTER TABLE ai_agent_chat_history ADD INDEX idx_ai_agent_chat_history_audio_id (audio_id);

-- -------------------------------------------------------------
-- 来源: 202512221117.sql
-- -------------------------------------------------------------
-- 更新豆包流式ASR供应器，增加end_window_size配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_DoubaoStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_DoubaoStreamASR', 'ASR', 'doubao_stream', '火山引擎语音识别(流式)', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"end_window_size","label":"静音判定时长(ms)","type":"number"}]', 3, 1, NOW(), 1, NOW());


-- 更新豆包流式ASR模型配置，增加end_window_size默认值
UPDATE `ai_model_config` SET
`config_json` = JSON_SET(`config_json`, '$.end_window_size', 200)
WHERE `id` = 'ASR_DoubaoStreamASR' AND JSON_EXTRACT(`config_json`, '$.end_window_size') IS NULL;

-- -------------------------------------------------------------
-- 来源: 202512301430.sql
-- -------------------------------------------------------------
-- 添加阿里百炼Paraformer实时语音识别服务配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_AliyunBLStream';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_AliyunBLStream', 'ASR', 'aliyunbl_stream', '阿里百炼Paraformer实时语音识别', '[{"key":"api_key","label":"API密钥","type":"password"},{"key":"model","label":"模型名称","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"}]', 18, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'ASR_AliyunBLStream';
INSERT INTO `ai_model_config` VALUES ('ASR_AliyunBLStream', 'ASR', 'AliyunBLStream', '阿里百炼Paraformer实时语音识别', 0, 1, '{"type": "aliyunbl_stream", "api_key": "", "model": "paraformer-realtime-v2", "format": "pcm", "sample_rate": 16000, "disfluency_removal_enabled": false, "semantic_punctuation_enabled": false, "max_sentence_silence": 200, "multi_threshold_mode_enabled": false, "punctuation_prediction_enabled": true, "inverse_text_normalization_enabled": true, "output_dir": "tmp/"}', 'https://help.aliyun.com/zh/model-studio/websocket-for-paraformer-real-time-service', '支持多语言、热词定制、语义断句等高级功能', 21, NULL, NULL, NULL, NULL);

-- 更新阿里百炼Paraformer模型配置的说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://help.aliyun.com/zh/model-studio/websocket-for-paraformer-real-time-service',
`remark` = '阿里百炼Paraformer实时语音识别配置说明：
1. 登录阿里云百炼平台 https://bailian.console.aliyun.com/
2. 创建API-KEY https://bailian.console.aliyun.com/#/api-key
3. 支持模型：paraformer-realtime-v2(推荐)、paraformer-realtime-8k-v2、paraformer-realtime-v1、paraformer-realtime-8k-v1
4. 功能特性：
   - 多语言支持(中文含方言、英文、日语、韩语、德语、法语、俄语)
   - 热词定制(vocabulary_id参数)，详细说明请参考：https://help.aliyun.com/zh/model-studio/custom-hot-words?
   - 语义断句/VAD断句(semantic_punctuation_enabled参数)
   - 自动标点符号、ITN、过滤语气词等
5. 参数说明：
   - model: 模型名称，推荐paraformer-realtime-v2
   - sample_rate: 采样率(Hz)，v2支持任意采样率，v1仅支持16000，8k版本仅支持8000
   - semantic_punctuation_enabled: false为VAD断句(低延迟)，true为语义断句(高准确)
   - max_sentence_silence: VAD断句静音时长阈值(200-6000ms)
' WHERE `id` = 'ASR_AliyunBLStream';


-- 更新豆包流式ASR供应器，增加配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_DoubaoStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_DoubaoStreamASR', 'ASR', 'doubao_stream', '火山引擎语音识别(流式)', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"cluster","label":"集群","type":"string"},{"key":"boosting_table_name","label":"热词文件名称","type":"string"},{"key":"correct_table_name","label":"替换词文件名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"end_window_size","label":"静音判定时长(ms)","type":"number"},{"key":"enable_multilingual","label":"是否开启多语种识别模式","type":"boolean"},{"key":"language","label":"指定语言编码","type":"string"}]', 3, 1, NOW(), 1, NOW());
UPDATE `ai_model_config` SET 
`remark` = '豆包ASR配置说明：
1. 豆包ASR和豆包(流式)ASR的区别是：豆包ASR是按次收费，豆包(流式)ASR是按时收费
2. 一般来说按次收费的更便宜，但是豆包(流式)ASR使用了大模型技术，效果更好
3. 需要在火山引擎控制台创建应用并获取appid和access_token
4. 支持中文语音识别
5. 需要网络连接
6. 输出文件保存在tmp/目录
申请步骤：
1. 访问 https://console.volcengine.com/speech/app
2. 创建新应用
3. 获取appid和access_token
4. 填入配置文件中
如需设置热词，请参考：https://www.volcengine.com/docs/6561/155738
如开启多语种识别模式，请设置language当该键为空时，该模型支持中英文、上海话、闽南语，四川、陕西、粤语识别。其他语种请参考：https://www.volcengine.com/docs/6561/1354869
' WHERE `id` = 'ASR_DoubaoStreamASR';

-- 更新豆包流式ASR模型配置，增加enable_multilingual默认值
UPDATE `ai_model_config` SET
`config_json` = JSON_SET(
    `config_json`, 
    '$.enable_multilingual', false,
    '$.language', 'zh-CN'
)
WHERE `id` = 'ASR_DoubaoStreamASR' 
AND JSON_EXTRACT(`config_json`, '$.enable_multilingual') IS NULL 
AND JSON_EXTRACT(`config_json`, '$.language') IS NULL;


-- 更新HuoshanDoubleStreamTTS供应器配置，增加多情感音色参数
UPDATE `ai_model_provider`
SET `fields` = '[{"key": "ws_url", "type": "string", "label": "WebSocket地址"}, {"key": "appid", "type": "string", "label": "应用ID"}, {"key": "access_token", "type": "string", "label": "访问令牌"}, {"key": "resource_id", "type": "string", "label": "资源ID"}, {"key": "speaker", "type": "string", "label": "默认音色"}, {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true}, {"key": "speech_rate", "type": "number", "label": "语速(-50~100)"}, {"key": "loudness_rate", "type": "number", "label": "音量(-50~100)"}, {"key": "pitch", "type": "number", "label": "音高(-12~12)"}, {"key": "emotion_scale", "type": "number", "label": "情感强度(1-5)"}, {"key": "emotion", "type": "string", "label": "情感类型"}]'
WHERE `id` = 'SYSTEM_TTS_HSDSTTS';

-- 更新默认值
UPDATE `ai_model_config` SET
`config_json` = JSON_SET(
    `config_json`,
    '$.emotion', 'neutral',
    '$.emotion_scale', 4
)
WHERE `id` = 'TTS_HuoshanDoubleStreamTTS'
AND JSON_EXTRACT(`config_json`, '$.emotion') IS NULL 
AND JSON_EXTRACT(`config_json`, '$.emotion_scale') IS NULL;

-- 增加文档链接和备注
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 链接复用：开启WebSocket连接复用，默认true减少链接损耗（注意：复用后设备处于聆听状态时空闲链接会占并发数）
7. 语速：-50~100，可不填，正常默认值0，可填-50~100
8. 音量：-50~100，可不填，正常默认值0，可填-50~100
9. 音高：-12~12，可不填，正常默认值0，可填-12~12
10. 多情感参数（当前仅部分音色支持设置情感）：
   相关音色列表：https://www.volcengine.com/docs/6561/1257544
    - emotion_scale：情感强度，可选值为：1~5，默认值为4
    - emotion：情感类型，可选值为：neutral、happy、sad、angry、fearful、disgusted、surprised
' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- -------------------------------------------------------------
-- 来源: 202601051433.sql
-- -------------------------------------------------------------
-- 更改FunASRServer说明文档模型为SenseVoiceSmall
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md',
`remark` = '独立部署FunASR，使用FunASR的API服务，只需要五句话
第一句：mkdir -p ./funasr-runtime-resources/models
第二句：sudo docker run -d -p 10096:10095 --privileged=true -v $PWD/funasr-runtime-resources/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
上一句话执行后会进入到容器，继续第三句：cd FunASR/runtime
不要退出容器，继续在容器中执行第四句：nohup bash run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir iic/SenseVoiceSmall-onnx  --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx  --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &
上一句话执行后会进入到容器，继续第五句：tail -f log.txt
第五句话执行完后，会看到模型下载日志，下载完后就可以连接使用了
以上是使用CPU推理，如果有GPU，详细参考：https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md' WHERE `id` = 'ASR_FunASRServer';

-- -------------------------------------------------------------
-- 来源: 202601141645.sql
-- -------------------------------------------------------------
-- 批量清理 ai_model_provider 中的 sample_rate 字段定义
UPDATE `ai_model_provider` ap
JOIN (
    SELECT 
        id,
        JSON_ARRAYAGG(
            JSON_OBJECT('key', jt.k, 'label', jt.l, 'type', jt.t)
        ) AS new_fields
    FROM `ai_model_provider`,
         JSON_TABLE(`fields`, '$[*]' COLUMNS (
             k VARCHAR(50) PATH '$.key',
             l VARCHAR(100) PATH '$.label',
             t VARCHAR(20) PATH '$.type'
         )) AS jt
    WHERE `model_type` = 'TTS' 
      AND jt.k != 'sample_rate'
    GROUP BY id
) filtered ON ap.id = filtered.id
SET ap.fields = filtered.new_fields;

-- 清理 config_json 顶层的 sample_rate
UPDATE `ai_model_config`
SET `config_json` = JSON_REMOVE(`config_json`, '$.sample_rate')
WHERE `model_type` = 'TTS'
  AND JSON_EXTRACT(`config_json`, '$.sample_rate') IS NOT NULL;

-- 清理Minimax流式TTS的sample_rate参数（位于audio_setting内部）
UPDATE `ai_model_config` SET 
`config_json` = JSON_SET(`config_json`, '$.audio_setting', JSON_REMOVE(JSON_EXTRACT(`config_json`, '$.audio_setting'), '$.sample_rate'))
WHERE `id` = 'TTS_MinimaxStreamTTS'
AND JSON_EXTRACT(`config_json`, '$.audio_setting.sample_rate') IS NOT NULL;

-- -------------------------------------------------------------
-- 来源: 202601231530.sql
-- -------------------------------------------------------------
-- 更新HuoshanDoubleStreamTTS供应器配置，将分散的参数改为JSON字典配置
-- 将 speech_rate, loudness_rate, pitch, emotion, emotion_scale 等参数整合为 audio_params, additions, mix_speaker 三个JSON字典

UPDATE `ai_model_provider`
SET `fields` = '[
  {"key": "ws_url", "type": "string", "label": "WebSocket地址"},
  {"key": "appid", "type": "string", "label": "应用ID"},
  {"key": "access_token", "type": "string", "label": "访问令牌"},
  {"key": "resource_id", "type": "string", "label": "资源ID"},
  {"key": "speaker", "type": "string", "label": "默认音色"},
  {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true},
  {"key": "audio_params", "type": "dict", "label": "音频输出配置"},
  {"key": "additions", "type": "dict", "label": "高级文本处理配置"},
  {"key": "mix_speaker", "type": "dict", "label": "混音控制配置"}
]'
WHERE `id` = 'SYSTEM_TTS_HSDSTTS';

-- 更新现有配置，将旧的分散参数迁移到新的JSON字典结构
UPDATE `ai_model_config`
SET `config_json` = JSON_SET(
    `config_json`,
    '$.audio_params', JSON_OBJECT(
        'speech_rate', CAST(COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.speech_rate')), ''), '0') AS SIGNED),
        'loudness_rate', CAST(COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.loudness_rate')), ''), '0') AS SIGNED)
    ),
    '$.additions', JSON_OBJECT(
        'aigc_metadata', JSON_OBJECT(),
        'cache_config', JSON_OBJECT(),
        'post_process', JSON_OBJECT(
            'pitch', CAST(COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.pitch')), ''), '0') AS SIGNED)
        )
    ),
    '$.mix_speaker', JSON_OBJECT()
)
WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- 删除旧的分散参数字段
UPDATE `ai_model_config`
SET `config_json` = JSON_REMOVE(
    `config_json`,
    '$.speech_rate',
    '$.loudness_rate',
    '$.pitch',
    '$.emotion',
    '$.emotion_scale'
)
WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- 更新文档链接和备注说明
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.volcengine.com/docs/6561/1329505',
`remark` = '火山引擎双向流式TTS配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
4. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
5. 链接复用：开启WebSocket连接复用，默认true减少链接损耗（注意：复用后设备处于聆听状态时空闲链接会占并发数）

详细参数文档：https://www.volcengine.com/docs/6561/1329505
【audio_params】音频输出配置 - 用户可自定义添加火山引擎支持的任何音频参数
  - speech_rate: 语速(-50~100)，默认0
  - loudness_rate: 音量(-50~100)，默认0
  - emotion: 情感类型（仅部分音色支持），可选值：neutral、happy、sad、angry、fearful、disgusted、surprised
  - emotion_scale: 情感强度(1~5)，默认4
  示例：{"speech_rate": 10, "loudness_rate": 5, "emotion": "happy", "emotion_scale": 4}

【additions】高级文本处理配置 - 用户可自定义添加火山引擎支持的任何高级参数
  - post_process.pitch: 音高(-12~12)，默认0
  - aigc_metadata: AIGC元数据配置
  - cache_config: 缓存配置
  示例：{"post_process": {"pitch": 2}, "aigc_metadata": {}, "cache_config": {}}

【mix_speaker】混音控制配置 - 多音色混合（仅 TTS 1.0）
  示例：
    {"speakers": [
      {"source_speaker": "zh_male_bvlazysheep","mix_factor": 0.3}, 
      {"source_speaker": "BV120_streaming","mix_factor": 0.3}, 
      {"source_speaker": "zh_male_ahu_conversation_wvae_bigtts","mix_factor": 0.4}
    ]}

注意：
- 多情感音色参数（emotion、emotion_scale）仅部分音色支持
- 相关音色列表：https://www.volcengine.com/docs/6561/1257544
- 用户可根据火山引擎API文档自行添加更多参数
- 混音功能主要适用于豆包语音合成模型1.0的音色，使用时需要将req_params.speaker设置为custom_mix_bigtts
'
WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';

-- -------------------------------------------------------------
-- 来源: 202601261730.sql
-- -------------------------------------------------------------
-- 更新小智参数中的默认采样率从 16000 改为 24000
UPDATE `sys_params`
SET `param_value` = '{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 24000,
    "channels": 1,
    "frame_duration": 60
  }
}'
WHERE `id` = 309 AND `param_code` = 'xiaozhi';

-- -------------------------------------------------------------
-- 来源: 202602021555.sql
-- -------------------------------------------------------------
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (502, 'system_error_response', '主人，小智现在有点忙，我们稍后再试吧。', 'string', 1, '系统错误时的回复');

-- -------------------------------------------------------------
-- 来源: 202602051017.sql
-- -------------------------------------------------------------
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

-- -------------------------------------------------------------
-- 来源: 202602051125.sql
-- -------------------------------------------------------------
-- 删除无用业务表ai_voiceprint
DROP TABLE IF EXISTS ai_voiceprint;

-- -------------------------------------------------------------
-- 来源: 202602061650.sql
-- -------------------------------------------------------------
-- 统一规范ai_tts_voice语言类型数据
UPDATE ai_tts_voice
SET languages = CASE
    WHEN languages IN ('中文', '普通话','东北话','天津话','中文-北京口音','中文-青岛口音','中文-河南口音','中文-广西口音','辽宁','陕西','中文-四川口音','中文-台湾口音','中文-长沙口音') THEN '普通话'
    WHEN languages IN ('中文及中英文混合', '中文、英文', '中文、美式英语','中文-北京口音、英文','中文(东北)及中英文混合') THEN '普通话、英语'
    WHEN languages IN ('英式英文', '英式英语', '美式英语', '澳洲英语', '英文') THEN '英语'
    WHEN languages = '日语' THEN '日语'
    WHEN languages = '日语、西语' THEN '日语、西班牙语'
    WHEN languages = '韩语' THEN '韩语'
    WHEN languages IN ('粤语', '中文-广东口音') THEN '粤语'
    WHEN languages = '中文(粤语)及中英文混合' THEN '粤语、英语'
    WHEN languages = '粤语及粤英混合' THEN '粤语、英语'
    ELSE languages
END;

-- 添加音色语言、音量、语速、音调字段到 ai_agent 表
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'tts_language');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `tts_language` VARCHAR(50) NULL COMMENT ''音色语言'' AFTER `tts_voice_id`', 'SELECT ''Column tts_language already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'tts_volume');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `tts_volume` INT NULL COMMENT ''TTS音量'' AFTER `tts_language`', 'SELECT ''Column tts_volume already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'tts_rate');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `tts_rate` INT NULL COMMENT ''TTS语速'' AFTER `tts_volume`', 'SELECT ''Column tts_rate already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'tts_pitch');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `tts_pitch` INT NULL COMMENT ''TTS音调'' AFTER `tts_rate`', 'SELECT ''Column tts_pitch already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 添加音色语言、音量、语速、音调字段到 ai_agent_template 表
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_template' AND COLUMN_NAME = 'tts_language');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent_template` ADD COLUMN `tts_language` VARCHAR(50) NULL COMMENT ''音色语言'' AFTER `tts_voice_id`', 'SELECT ''Column tts_language already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_template' AND COLUMN_NAME = 'tts_volume');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent_template` ADD COLUMN `tts_volume` INT NULL COMMENT ''TTS音量'' AFTER `tts_language`', 'SELECT ''Column tts_volume already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_template' AND COLUMN_NAME = 'tts_rate');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent_template` ADD COLUMN `tts_rate` INT NULL COMMENT ''TTS语速'' AFTER `tts_volume`', 'SELECT ''Column tts_rate already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_template' AND COLUMN_NAME = 'tts_pitch');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent_template` ADD COLUMN `tts_pitch` INT NULL COMMENT ''TTS音调'' AFTER `tts_rate`', 'SELECT ''Column tts_pitch already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------
-- 来源: 202602271137.sql
-- -------------------------------------------------------------
-- 更新腾讯TTS供应器配置，增加speed、volume和format参数
UPDATE `ai_model_provider`
SET fields = '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"format","label":"音频格式","type":"string"},{"key":"speed","label":"语速","type":"number"},{"key":"volume","label":"音量","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"voice","label":"音色ID","type":"string"},{"key":"region","label":"区域","type":"string"}]'
WHERE id = 'SYSTEM_TTS_TencentTTS';

-- 更新腾讯TTS模型配置，增加speed和volume参数，补充参数说明
UPDATE `ai_model_config` SET 
    `config_json` = JSON_SET(`config_json`, '$.speed', 0, '$.volume', 0),
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
5. 填入配置文件中
音频参数：
- format: 音频格式，支持pcm、wav、mp3
- speed: 语速，范围-2~6，默认0
- volume: 音量，范围-10~10，默认0'
WHERE `id` = 'TTS_TencentTTS';

-- 更新CozeCnTTS供应器配置，增加speed和loudness_rate参数
UPDATE `ai_model_provider`
SET fields = '[{"key":"voice","label":"音色","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"speed","label":"语速","type":"number"},{"key":"loudness_rate","label":"音量增益","type":"number"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"response_format","label":"响应格式","type":"string"}]'
WHERE id = 'SYSTEM_TTS_cozecn';

-- 更新CozeCnTTS模型配置，增加speed和loudness_rate参数，补充参数说明
UPDATE `ai_model_config` SET 
    `config_json` = JSON_SET(`config_json`, '$.speed', 1, '$.loudness_rate', 0),
    `remark` = 'Coze中文语音合成配置说明：
1. 访问 https://www.coze.cn/ 注册并登录
2. 创建应用并获取access_token
3. 选择合适的音色ID
音频参数：
- response_format: 音频格式，支持pcm、wav、mp3
- speed: 语速，范围0.5~2，默认1
- loudness_rate: 音量增益，范围-50~100，默认0'
WHERE `id` = 'TTS_CozeCnTTS';

-- -------------------------------------------------------------
-- 来源: 202602281000.sql
-- -------------------------------------------------------------
-- 标签表
CREATE TABLE IF NOT EXISTS ai_agent_tag (
    id VARCHAR(32) NOT NULL COMMENT '主键',
    tag_name VARCHAR(64) NOT NULL COMMENT '标签名称',
    sort INT UNSIGNED DEFAULT 0 COMMENT '排序',
    creator BIGINT COMMENT '创建者',
    created_at DATETIME COMMENT '创建时间',
    updater BIGINT COMMENT '更新者',
    updated_at DATETIME COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    PRIMARY KEY (id),
    UNIQUE KEY uk_tag_name (tag_name),
    INDEX idx_sort (sort)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体标签表';

-- 智能体标签关联表
CREATE TABLE IF NOT EXISTS ai_agent_tag_relation (
    id VARCHAR(32) NOT NULL COMMENT '主键',
    agent_id VARCHAR(32) NOT NULL COMMENT '智能体ID',
    tag_id VARCHAR(32) NOT NULL COMMENT '标签ID',
    creator BIGINT COMMENT '创建者',
    created_at DATETIME COMMENT '创建时间',
    updater BIGINT COMMENT '更新者',
    updated_at DATETIME COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_agent_tag (agent_id, tag_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_tag_id (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体标签关联表';

-- -------------------------------------------------------------
-- 来源: 202603091051.sql
-- -------------------------------------------------------------
-- 给智能体标签关联表添加排序字段
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_tag_relation' AND COLUMN_NAME = 'sort');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent_tag_relation` ADD COLUMN `sort` INT UNSIGNED DEFAULT 0 COMMENT ''排序''', 'SELECT ''Column sort already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 修复现有数据（仅当 sort 字段为默认值 0 时执行，避免覆盖用户已设置的顺序）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent_tag_relation' AND COLUMN_NAME = 'sort');
SET @sql = IF(@col_exists > 0 AND (SELECT COUNT(*) FROM ai_agent_tag_relation WHERE sort = 0) > 0, 
    'UPDATE ai_agent_tag_relation r INNER JOIN (SELECT id, ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at) AS row_num FROM ai_agent_tag_relation) t ON r.id = t.id SET r.sort = t.row_num', 
    'SELECT ''No need to update or column does not exist'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------
-- 来源: 202603101723.sql
-- -------------------------------------------------------------
-- 给声音克隆表添加语言字段
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_voice_clone' AND COLUMN_NAME = 'languages');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_voice_clone` ADD COLUMN `languages` VARCHAR(50) DEFAULT NULL COMMENT ''语言'' AFTER `voice_id`', 'SELECT ''Column languages already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------
-- 来源: 202603111131.sql
-- -------------------------------------------------------------
-- 增加一下ragflow返回的参数（创建/查询知识库时返回）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'tenant_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `tenant_id` varchar(32) DEFAULT NULL COMMENT ''租户ID''', 'SELECT ''Column tenant_id already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'avatar');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `avatar` text DEFAULT NULL COMMENT ''知识库头像 (Base64)''', 'SELECT ''Column avatar already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'embedding_model');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `embedding_model` varchar(50) DEFAULT NULL COMMENT ''嵌入模型名称''', 'SELECT ''Column embedding_model already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'permission');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `permission` varchar(20) DEFAULT ''me'' COMMENT ''权限设置：me/team''', 'SELECT ''Column permission already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'chunk_method');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `chunk_method` varchar(50) DEFAULT NULL COMMENT ''分块方法''', 'SELECT ''Column chunk_method already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'parser_config');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `parser_config` text DEFAULT NULL COMMENT ''解析器配置 (JSON)''', 'SELECT ''Column parser_config already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'chunk_count');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `chunk_count` bigint(20) DEFAULT 0 COMMENT ''分块总数''', 'SELECT ''Column chunk_count already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'document_count');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `document_count` bigint(20) DEFAULT 0 COMMENT ''文档总数''', 'SELECT ''Column document_count already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'token_num');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `token_num` bigint(20) DEFAULT 0 COMMENT ''总 Token 数''', 'SELECT ''Column token_num already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 文档表 (Shadow DB for RAGFlow)
-- 留存一份文档id，把ragflow远端文档id和本地id关联起来（只是备份一份元信息链接，实际上文件内容的存储还是在ragflow）
DROP TABLE IF EXISTS `ai_rag_knowledge_document`;
CREATE TABLE `ai_rag_knowledge_document` (
     `id` varchar(36) NOT NULL COMMENT '本地唯一ID',
     `dataset_id` varchar(36) NOT NULL COMMENT '知识库ID (关联 ai_rag_dataset)',
     `document_id` varchar(64) NOT NULL COMMENT 'RAGFlow文档ID (远程ID)',
     `name` varchar(255) DEFAULT NULL COMMENT '文档名称',
     `size` bigint(20) DEFAULT NULL COMMENT '文件大小(Bytes)',
     `type` varchar(20) DEFAULT NULL COMMENT '文件类型',
     `chunk_method` varchar(50) DEFAULT NULL COMMENT '分块方法',
     `parser_config` text COMMENT '解析配置(JSON)',
     `status` varchar(10) DEFAULT '1' COMMENT '可用状态 (1:启用 0:禁用)',
     `run` varchar(32) DEFAULT 'UNSTART' COMMENT '运行状态 (UNSTART/RUNNING/CANCEL/DONE/FAIL)',
     `progress` double DEFAULT '0' COMMENT '解析进度 (0.0 ~ 1.0)',
     `thumbnail` mediumtext COMMENT '缩略图 (Base64 或 URL)',
     `process_duration` double DEFAULT '0' COMMENT '解析耗时 (单位: 秒)',
     `meta_fields` text COMMENT '自定义元数据 (JSON)',
     `source_type` varchar(32) DEFAULT 'local' COMMENT '来源类型 (local, s3, url 等)',
     `error` text COMMENT '错误信息',
     `chunk_count` int(11) DEFAULT '0' COMMENT '分块数量',
     `token_count` bigint(20) DEFAULT '0' COMMENT 'Token数量',
     `enabled` tinyint(1) DEFAULT '1' COMMENT '启用状态',
     `creator` bigint(20) DEFAULT NULL COMMENT '创建者',
     `created_at` datetime DEFAULT NULL COMMENT '创建时间',
     `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
     `last_sync_at` datetime DEFAULT NULL COMMENT '最后同步时间',
     PRIMARY KEY (`id`),
     UNIQUE KEY `uk_doc_id` (`document_id`),
     KEY `idx_dataset_id` (`dataset_id`),
     KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档表';

-- -------------------------------------------------------------
-- 来源: 202603231037.sql
-- -------------------------------------------------------------
-- 新增仅上报聊天记录记忆模型供应器

delete from `ai_model_provider` where `id` = 'SYSTEM_Memory_mem_report_only';
delete from `ai_model_config` where `id` = 'Memory_mem_report_only';

INSERT INTO `ai_model_provider` VALUES ('SYSTEM_Memory_mem_report_only', 'Memory', 'mem_report_only', '仅上报聊天记录', '[]', 4, 1, NOW(), 1, NOW());
INSERT INTO `ai_model_config` VALUES ('Memory_mem_report_only', 'Memory', 'mem_report_only', '仅上报聊天记录', 0, 1, '{"type": "mem_report_only"}', NULL, '仅上报聊天记录，不总结记忆', 3, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202603311200.sql
-- -------------------------------------------------------------
-- 修改聊天内容字段类型
ALTER TABLE ai_agent_chat_history MODIFY COLUMN content TEXT COMMENT '聊天内容';

-- -------------------------------------------------------------
-- 来源: 202604010930.sql
-- -------------------------------------------------------------
-- 修改记忆模型名称

UPDATE `ai_model_config` SET `model_name` = '本地短期记忆（总结记忆）' WHERE `id` = 'Memory_mem_local_short';
UPDATE `ai_model_provider` SET `name` = '本地短期记忆（总结记忆）' WHERE `id` = 'SYSTEM_Memory_mem_local_short';

UPDATE `ai_model_config` SET `model_name` = '仅上报聊天记录（不总结记忆）' WHERE `id` = 'Memory_mem_report_only';
UPDATE `ai_model_provider` SET `name` = '仅上报聊天记录（不总结记忆）' WHERE `id` = 'SYSTEM_Memory_mem_report_only';

-- -------------------------------------------------------------
-- 来源: 202604011035.sql
-- -------------------------------------------------------------
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (312, 'tool_call_timeout', '30', 'number', 1, '工具调用超时时间(秒)');

-- -------------------------------------------------------------
-- 来源: 202604011545.sql
-- -------------------------------------------------------------
-- 智能体表添加小模型ID字段
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'slm_model_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `slm_model_id` VARCHAR(255) NULL COMMENT ''小模型ID'' AFTER `llm_model_id`', 'SELECT ''Column slm_model_id already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 创建聊天标题表
DROP TABLE IF EXISTS `ai_agent_chat_title`;
CREATE TABLE `ai_agent_chat_title` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键ID',
    `session_id` VARCHAR(255) NOT NULL COMMENT '会话ID',
    `title` VARCHAR(255) DEFAULT NULL COMMENT '聊天标题',
    `created_at` DATETIME DEFAULT NULL COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT NULL COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体聊天标题表';

-- -------------------------------------------------------------
-- 来源: 202604161357.sql
-- -------------------------------------------------------------
-- 更新模型名称：qwen2.5-vl-3b-instruct 改为 qwen3.5-flash
UPDATE `ai_model_config` 
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'qwen3.5-flash')
WHERE `id` = 'VLLM_QwenVLVLLM' 
AND JSON_EXTRACT(`config_json`, '$.model_name') = 'qwen2.5-vl-3b-instruct';

-- 更新模型名称：qwen-turbo 改为 qwen-flash
UPDATE `ai_model_config` 
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'qwen-flash')
WHERE `id` = 'LLM_AliLLM' 
AND JSON_EXTRACT(`config_json`, '$.model_name') = 'qwen-turbo';

-- 更新备注：qwen-turbo 改为 qwen-flash
UPDATE `ai_model_config` 
SET `remark` = REPLACE(`remark`, 'qwen-turbo', 'qwen-flash')
WHERE `id` = 'LLM_AliLLM' 
AND `remark` LIKE '%qwen-turbo%';

-- -------------------------------------------------------------
-- 来源: 202604201719.sql
-- -------------------------------------------------------------
-- 新增豆包语音合成模型2.0供应器（使用seed-tts-2.0资源ID）
-- 与火山双流式TTS配置相同，但resource_id固定为seed-tts-2.0

-- 插入豆包语音合成模型2.0供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS_V2';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_HSDSTTS_V2', 'TTS', 'huoshan_double_stream', '豆包语音合成模型2.0', '[
  {"key": "ws_url", "type": "string", "label": "WebSocket地址"},
  {"key": "appid", "type": "string", "label": "应用ID"},
  {"key": "access_token", "type": "string", "label": "访问令牌"},
  {"key": "resource_id", "type": "string", "label": "资源ID"},
  {"key": "speaker", "type": "string", "label": "默认音色"},
  {"key": "enable_ws_reuse", "type": "boolean", "label": "是否开启链接复用", "default": true},
  {"key": "audio_params", "type": "dict", "label": "音频输出配置"},
  {"key": "additions", "type": "dict", "label": "高级文本处理配置"},
  {"key": "mix_speaker", "type": "dict", "label": "混音控制配置"}
]', 14, 1, NOW(), 1, NOW());

-- 插入豆包语音合成模型2.0配置
delete from `ai_model_config` where id = 'TTS_HSDSTTS_V2';
INSERT INTO `ai_model_config` VALUES ('TTS_HSDSTTS_V2', 'TTS', 'HuoshanDoubleStreamTTSV2', '豆包语音合成模型2.0', 0, 1, '{
  "type": "huoshan_double_stream",
  "ws_url": "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
  "appid": "",
  "access_token": "",
  "resource_id": "seed-tts-2.0",
  "speaker": "zh_female_xiaohe_uranus_bigtts",
  "enable_ws_reuse": true,
  "audio_params": {
    "speech_rate": 0,
    "loudness_rate": 0
  },
  "additions": {
    "aigc_metadata": {},
    "cache_config": {},
    "post_process": {
      "pitch": 0
    }
  },
  "mix_speaker": {}
}', NULL, NULL, 17, NULL, NULL, NULL, NULL);

-- 豆包语音合成模型2.0配置说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.volcengine.com/docs/6561/1329505',
`remark` = '豆包语音合成模型2.0配置说明（基于火山引擎seed-tts-2.0）：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10035 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
4. 资源ID固定为：seed-tts-2.0（豆包语音合成模型2.0）
5. 链接复用：开启WebSocket连接复用，默认true减少链接损耗（注意：复用后设备处于聆听状态时空闲链接会占并发数）

详细参数文档：https://www.volcengine.com/docs/6561/1329505
【audio_params】音频输出配置 - 用户可自定义添加火山引擎支持的任何音频参数
  - speech_rate: 语速(-50~100)，默认0
  - loudness_rate: 音量(-50~100)，默认0
  示例：{"speech_rate": 10, "loudness_rate": 5}

【additions】高级文本处理配置 - 用户可自定义添加火山引擎支持的任何高级参数
  - post_process.pitch: 音高(-12~12)，默认0
  - aigc_metadata: AIGC元数据配置
  - cache_config: 缓存配置
  示例：{"post_process": {"pitch": 2}, "aigc_metadata": {}, "cache_config": {}}

注意：
- 豆包语音合成模型2.0使用seed-tts-2.0资源ID，与火山双流式TTS（volc.service_type.10029）不同
- 相关音色列表：https://www.volcengine.com/docs/6561/1257544
- 用户可根据火山引擎API文档自行添加更多参数
' WHERE `id` = 'TTS_HSDSTTS_V2';

-- 添加豆包语音合成模型2.0音色（与火山双流式TTS音色相同）
delete from `ai_tts_voice` where tts_model_id = 'TTS_HSDSTTS_V2';
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0001', 'TTS_HSDSTTS_V2', 'Vivi', 'zh_female_vv_uranus_bigtts', '普通话、日语、印尼语、墨西哥西班牙语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_vv_uranus_bigtts.wav', NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0002', 'TTS_HSDSTTS_V2', '小何', 'zh_female_xiaohe_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_xiaohe_uranus_bigtts.mp3', NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0003', 'TTS_HSDSTTS_V2', '云舟', 'zh_male_m191_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_m191_uranus_bigtts.mp3', NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0004', 'TTS_HSDSTTS_V2', '小天', 'zh_male_taocheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_taocheng_uranus_bigtts.mp3', NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0005', 'TTS_HSDSTTS_V2', '刘飞', 'zh_male_liufei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_liufei_uranus_bigtts.mp3', NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0006', 'TTS_HSDSTTS_V2', '魅力苏菲', 'zh_female_sophie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sophie_uranus_bigtts.mp3', NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0007', 'TTS_HSDSTTS_V2', '清新女声', 'zh_female_qingxinnvsheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_qingxinnvsheng_uranus_bigtts.mp3', NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0008', 'TTS_HSDSTTS_V2', '知性灿灿', 'zh_female_cancan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_cancan_uranus_bigtts.mp3', NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0009', 'TTS_HSDSTTS_V2', '撒娇学妹', 'zh_female_sajiaoxuemei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_sajiaoxuemei_uranus_bigtts.mp3', NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0010', 'TTS_HSDSTTS_V2', '甜美小源', 'zh_female_tianmeixiaoyuan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeixiaoyuan_uranus_bigtts.mp3', NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0011', 'TTS_HSDSTTS_V2', '甜美桃子', 'zh_female_tianmeitaozi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeitaozi_uranus_bigtts.mp3', NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0012', 'TTS_HSDSTTS_V2', '爽快思思', 'zh_female_shuangkuaisisi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_shuangkuaisisi_uranus_bigtts.mp3', NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0013', 'TTS_HSDSTTS_V2', '佩奇猪', 'zh_female_peiqi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_peiqi_uranus_bigtts.mp3', NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0014', 'TTS_HSDSTTS_V2', '邻家女孩', 'zh_female_linjianvhai_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_linjianvhai_uranus_bigtts.mp3', NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0015', 'TTS_HSDSTTS_V2', '少年梓辛/Brayan', 'zh_male_shaonianzixin_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_shaonianzixin_uranus_bigtts.mp3', NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0016', 'TTS_HSDSTTS_V2', '猴哥', 'zh_male_sunwukong_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sunwukong_uranus_bigtts.mp3', NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0017', 'TTS_HSDSTTS_V2', '魅力女友', 'zh_female_meilinvyou_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_meilinvyou_uranus_bigtts.mp3', NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0018', 'TTS_HSDSTTS_V2', 'Tim', 'en_male_tim_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_male_tim_uranus_bigtts.mp3', NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0019', 'TTS_HSDSTTS_V2', 'Dacey', 'en_female_dacey_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_dacey_uranus_bigtts.mp3', NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0020', 'TTS_HSDSTTS_V2', 'Stokie', 'en_female_stokie_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_stokie_uranus_bigtts.mp3', NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0021', 'TTS_HSDSTTS_V2', '温暖阿虎/Alvin', 'zh_male_wennuanahu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_wennuanahu_uranus_bigtts.mp3', NULL, NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0022', 'TTS_HSDSTTS_V2', '奶气萌娃', 'zh_male_naiqimengwa_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_naiqimengwa_uranus_bigtts.mp3', NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0023', 'TTS_HSDSTTS_V2', '婆婆', 'zh_female_popo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_popo_uranus_bigtts.mp3', NULL, NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0024', 'TTS_HSDSTTS_V2', '开朗姐姐', 'zh_female_kailangjiejie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_kailangjiejie_uranus_bigtts.mp3', NULL, NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0025', 'TTS_HSDSTTS_V2', '轻盈朵朵', 'saturn_zh_female_qingyingduoduo_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_qingyingduoduo_cs_tob.mp3', NULL, NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0026', 'TTS_HSDSTTS_V2', '温婉珊珊', 'saturn_zh_female_wenwanshanshan_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_wenwanshanshan_cs_tob.mp3', NULL, NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0027', 'TTS_HSDSTTS_V2', '霸气青叔', 'zh_male_baqiqingshu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_baqiqingshu_uranus_bigtts.mp3', NULL, NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0028', 'TTS_HSDSTTS_V2', '悬疑解说', 'zh_male_xuanyijieshuo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_xuanyijieshuo_uranus_bigtts.mp3', NULL, NULL, NULL, 28, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0029', 'TTS_HSDSTTS_V2', '古风少御', 'zh_female_gufengshaoyu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_gufengshaoyu_uranus_bigtts.mp3', NULL, NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0030', 'TTS_HSDSTTS_V2', '唐僧', 'zh_male_tangseng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_tangseng_uranus_bigtts.mp3', NULL, NULL, NULL, 30, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202604211515.sql
-- -------------------------------------------------------------
-- 智能体替换词文件表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_file` (
    `id`          VARCHAR(32)  NOT NULL,
    `file_name`   VARCHAR(256) NOT NULL COMMENT '原始文件名',
    `word_count`  INT          NOT NULL DEFAULT 0 COMMENT '替换词数量',
    `content`     TEXT         COMMENT '文件原始内容',
    `creator`     BIGINT       DEFAULT NULL,
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updater`     BIGINT       DEFAULT NULL,
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_creator` (`creator`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='替换词文件';

-- 替换词词条表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_item` (
    `id`          VARCHAR(32)  NOT NULL,
    `file_id`     VARCHAR(32)  NOT NULL COMMENT '所属文件ID',
    `source_word` VARCHAR(128) NOT NULL COMMENT '原词',
    `target_word` VARCHAR(128) NOT NULL COMMENT '替换词',
    PRIMARY KEY (`id`),
    INDEX `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='替换词词条';

-- 智能体替换词文件关联表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_mapping` (
    `id`          VARCHAR(32)  NOT NULL,
    `agent_id`    VARCHAR(32)  NOT NULL,
    `file_id`     VARCHAR(32)  NOT NULL,
    `creator`     BIGINT       DEFAULT NULL,
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updater`     BIGINT       DEFAULT NULL,
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `uk_agent_file` (`agent_id`, `file_id`),
    INDEX `idx_agent_id` (`agent_id`),
    INDEX `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体替换词文件关联';

-- -------------------------------------------------------------
-- 来源: 202604211700.sql
-- -------------------------------------------------------------
-- 修复豆包语音合成模型2.0 provider_code 重复问题，添加 ASR 2.0 支持

-- ==================== 豆包语音合成模型2.0 ====================
-- 删除 TTS 2.0 供应器（不再需要单独的供应器）
delete from `ai_model_provider` where id = 'SYSTEM_TTS_HSDSTTS_V2';

-- ==================== 豆包语音识别(流式) ====================
-- 修正原有豆包语音识别(流式)供应器，移除cluster字段，添加resource_id字段
UPDATE `ai_model_provider` SET `fields` = '[{"key":"appid","type":"string","label":"应用ID"},{"key":"access_token","type":"string","label":"访问令牌"},{"key":"boosting_table_name","type":"string","label":"热词文件名称"},{"key":"correct_table_name","type":"string","label":"替换词文件名称"},{"key":"output_dir","type":"string","label":"输出目录"},{"key":"end_window_size","type":"number","label":"静音判定时长(ms)"},{"key":"enable_multilingual","type":"boolean","label":"是否开启多语种识别模式"},{"key":"language","type":"string","label":"指定语言编码"},{"key":"resource_id","type":"string","label":"资源ID"}]' WHERE `id` = 'SYSTEM_ASR_DoubaoStreamASR';

-- 修正原有豆包语音识别(流式)配置，移除cluster字段，添加resource_id默认值
UPDATE `ai_model_config` SET `config_json` = JSON_REMOVE(JSON_SET(`config_json`, '$.resource_id', 'volc.bigasr.sauc.duration'), '$.cluster') WHERE `id` = 'ASR_DoubaoStreamASR';

-- ==================== 豆包语音识别模型2.0 ====================

-- 插入豆包语音识别模型2.0配置
delete from `ai_model_config` where id = 'ASR_DoubaoStreamASRV2';
INSERT INTO `ai_model_config` VALUES ('ASR_DoubaoStreamASRV2', 'ASR', 'DoubaoStreamASRV2', '豆包语音识别模型2.0', 0, 1, '{
  "type": "doubao_stream",
  "appid": "",
  "access_token": "",
  "resource_id": "volc.seedasr.sauc.duration",
  "end_window_size": 200,
  "enable_multilingual": false,
  "language": "zh-CN",
  "output_dir": "tmp/"
}', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- 豆包语音识别模型2.0配置说明文档
UPDATE `ai_model_config` SET
`doc_link` = 'https://www.volcengine.com/docs/6561/109979',
`remark` = '豆包语音识别模型2.0配置说明（基于火山引擎seed-asr）：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10038 开通豆包流式语音识别模型2.0
3. 在页面底部获取appid和access_token
4. 资源ID有两种：小时版（volc.seedasr.sauc.duration）和并发版（volc.seedasr.sauc.concurrent）
   - 小时版：固定为：volc.seedasr.sauc.duration（豆包语音识别模型2.0）
   - 并发版：固定为：volc.seedasr.sauc.concurrent（豆包语音识别模型2.0）

详细参数文档：https://www.volcengine.com/docs/6561/109979

注意：
- 豆包语音识别模型2.0使用volc.seedasr.sauc.duration资源ID，与豆包语音识别(流式)（volc.bigasr.sauc.duration）不同
- 语音识别模型2.0价格更为便宜，建议在高并发场景下使用并发版资源ID
' WHERE `id` = 'ASR_DoubaoStreamASRV2';

-- -------------------------------------------------------------
-- 来源: 202604300930.sql
-- -------------------------------------------------------------
-- 修改模型名称
UPDATE `ai_model_config` SET `model_name` = '豆包语音识别2.0(流式)' WHERE `id` = 'ASR_DoubaoStreamASRV2';

UPDATE `ai_model_config` SET `model_name` = '豆包语音合成2.0(流式)' WHERE `id` = 'TTS_HSDSTTS_V2';

-- 调整模型音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_HSDSTTS_V2';

-- 通用场景 and 视频配音
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0001', 'TTS_HSDSTTS_V2', '湾湾小何', 'zh_female_xiaohe_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_xiaohe_uranus_bigtts.mp3', NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0002', 'TTS_HSDSTTS_V2', 'Vivi', 'zh_female_vv_uranus_bigtts', '普通话、日语、印尼语、墨西哥西班牙语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_vv_uranus_bigtts.wav', NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0003', 'TTS_HSDSTTS_V2', '可爱女生', 'saturn_zh_female_keainvsheng_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/saturn_zh_female_keainvsheng_tob.wav', NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0004', 'TTS_HSDSTTS_V2', '调皮公主', 'saturn_zh_female_tiaopigongzhu_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/saturn_zh_female_tiaopigongzhu_tob.wav', NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0005', 'TTS_HSDSTTS_V2', '阳光青年', 'zh_male_yangguangqingnian_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_yangguangqingnian_uranus_bigtts.mp3', NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0006', 'TTS_HSDSTTS_V2', '爽朗少年', 'saturn_zh_male_shuanglangshaonian_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/saturn_zh_male_shuanglangshaonian_tob.wav', NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0007', 'TTS_HSDSTTS_V2', '爽朗少年', 'saturn_zh_male_tiancaitongzhuo_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/saturn_zh_male_tiancaitongzhuo_tob.wav', NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0008', 'TTS_HSDSTTS_V2', '大壹', 'zh_male_dayi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_dayi_saturn_bigtts.wav', NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0009', 'TTS_HSDSTTS_V2', '黑猫侦探社咪仔', 'zh_female_mizai_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_mizai_saturn_bigtts.wav', NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0010', 'TTS_HSDSTTS_V2', '鸡汤女', 'zh_female_jitangnv_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_jitangnv_saturn_bigtts.wav', NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0011', 'TTS_HSDSTTS_V2', '魅力女友', 'zh_female_meilinvyou_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_meilinvyou_saturn_bigtts.wav', NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0012', 'TTS_HSDSTTS_V2', '流畅女声', 'zh_female_liuchangnv_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/%E6%B5%81%E7%95%85%E5%A5%B3%E5%A3%B0.wav', NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0013', 'TTS_HSDSTTS_V2', '儒雅逸辰', 'zh_male_ruyayichen_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_ruyayichen_saturn_bigtts.wav', NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0014', 'TTS_HSDSTTS_V2', '云舟', 'zh_male_m191_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_m191_uranus_bigtts.mp3', NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0015', 'TTS_HSDSTTS_V2', '小天', 'zh_male_taocheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_taocheng_uranus_bigtts.mp3', NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0016', 'TTS_HSDSTTS_V2', '刘飞', 'zh_male_liufei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_liufei_uranus_bigtts.mp3', NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0017', 'TTS_HSDSTTS_V2', '魅力苏菲', 'zh_female_sophie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sophie_uranus_bigtts.mp3', NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0018', 'TTS_HSDSTTS_V2', '清新女声', 'zh_female_qingxinnvsheng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_qingxinnvsheng_uranus_bigtts.mp3', NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0019', 'TTS_HSDSTTS_V2', '知性灿灿', 'zh_female_cancan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_cancan_uranus_bigtts.mp3', NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0020', 'TTS_HSDSTTS_V2', '撒娇学妹', 'zh_female_sajiaoxuemei_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_sajiaoxuemei_uranus_bigtts.mp3', NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0021', 'TTS_HSDSTTS_V2', '甜美小源', 'zh_female_tianmeixiaoyuan_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeixiaoyuan_uranus_bigtts.mp3', NULL, NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0022', 'TTS_HSDSTTS_V2', '甜美桃子', 'zh_female_tianmeitaozi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_tianmeitaozi_uranus_bigtts.mp3', NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0023', 'TTS_HSDSTTS_V2', '邻家女孩', 'zh_female_linjianvhai_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_linjianvhai_uranus_bigtts.mp3', NULL, NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0024', 'TTS_HSDSTTS_V2', '爽快思思', 'zh_female_shuangkuaisisi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_shuangkuaisisi_uranus_bigtts.mp3', NULL, NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0025', 'TTS_HSDSTTS_V2', '少年梓辛/Brayan', 'zh_male_shaonianzixin_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_shaonianzixin_uranus_bigtts.mp3', NULL, NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0026', 'TTS_HSDSTTS_V2', '温暖阿虎/Alvin', 'zh_male_wennuanahu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_wennuanahu_uranus_bigtts.mp3', NULL, NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0027', 'TTS_HSDSTTS_V2', '奶气萌娃', 'zh_male_naiqimengwa_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_naiqimengwa_uranus_bigtts.mp3', NULL, NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0028', 'TTS_HSDSTTS_V2', '婆婆', 'zh_female_popo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_popo_uranus_bigtts.mp3', NULL, NULL, NULL, 28, NULL, NULL, NULL, NULL);

-- 客服场景
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0029', 'TTS_HSDSTTS_V2', '轻盈朵朵', 'saturn_zh_female_qingyingduoduo_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_qingyingduoduo_cs_tob.mp3', NULL, NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0030', 'TTS_HSDSTTS_V2', '温婉珊珊', 'saturn_zh_female_wenwanshanshan_cs_tob', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/ICL_zh_female_wenwanshanshan_cs_tob.mp3', NULL, NULL, NULL, 30, NULL, NULL, NULL, NULL);

-- 多语种
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0031', 'TTS_HSDSTTS_V2', 'Tim', 'en_male_tim_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_male_tim_uranus_bigtts.mp3', NULL, NULL, NULL, 31, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0032', 'TTS_HSDSTTS_V2', 'Dacey', 'en_female_dacey_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_dacey_uranus_bigtts.mp3', NULL, NULL, NULL, 32, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0033', 'TTS_HSDSTTS_V2', 'Stokie', 'en_female_stokie_uranus_bigtts', '英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/en_female_stokie_uranus_bigtts.mp3', NULL, NULL, NULL, 33, NULL, NULL, NULL, NULL);

-- 有声阅读
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0034', 'TTS_HSDSTTS_V2', '古风少御', 'zh_female_gufengshaoyu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_gufengshaoyu_uranus_bigtts.mp3', NULL, NULL, NULL, 34, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0035', 'TTS_HSDSTTS_V2', '霸气青叔', 'zh_male_baqiqingshu_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_baqiqingshu_uranus_bigtts.mp3', NULL, NULL, NULL, 35, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0036', 'TTS_HSDSTTS_V2', '悬疑解说', 'zh_male_xuanyijieshuo_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_xuanyijieshuo_uranus_bigtts.mp3', NULL, NULL, NULL, 36, NULL, NULL, NULL, NULL);

-- 角色扮演
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0037', 'TTS_HSDSTTS_V2', '佩奇猪', 'zh_female_peiqi_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_female_peiqi_uranus_bigtts.mp3', NULL, NULL, NULL, 37, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0038', 'TTS_HSDSTTS_V2', '猴哥', 'zh_male_sunwukong_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_sunwukong_uranus_bigtts.mp3', NULL, NULL, NULL, 38, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0039', 'TTS_HSDSTTS_V2', '猪八戒', 'zh_male_zhubajie_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_zhubajie_uranus_bigtts.mp3', NULL, NULL, NULL, 39, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_HSDSTTS_V2_0040', 'TTS_HSDSTTS_V2', '唐僧', 'zh_male_tangseng_uranus_bigtts', '普通话、英语', 'https://lf3-static.bytednsdoc.com/obj/eden-cn/lm_hz_ihsph/ljhwZthlaukjlkulzlp/portal/bigtts/zh_male_tangseng_uranus_bigtts.mp3', NULL, NULL, NULL, 40, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202605071037.sql
-- -------------------------------------------------------------
-- 删除provider_code为ttson的供应器
DELETE FROM `ai_model_provider` WHERE `provider_code` = 'ttson';

-- 删除model_code为ACGNTTS的配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'ACGNTTS';

-- -------------------------------------------------------------
-- 来源: 202605071120.sql
-- -------------------------------------------------------------
-- 删除model_code为GizwitsTTS的配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'GizwitsTTS';

-- 删除关联的TTS音色记录
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_GizwitsTTS';
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_ACGNTTS';

-- -------------------------------------------------------------
-- 来源: 202605081008.sql
-- -------------------------------------------------------------
-- 删除provider_code为linkerai的供应商配置
DELETE FROM `ai_model_provider` WHERE `provider_code` = 'linkerai';

-- 删除model_code为LinkeraiTTS的模型配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'LinkeraiTTS';

-- 删除LinkeraiTTS关联的TTS音色记录
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_LinkeraiTTS';

-- -------------------------------------------------------------
-- 来源: 202605121509.sql
-- -------------------------------------------------------------
-- 新增联网搜索工具配置字段
SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_WEB_SEARCH');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_WEB_SEARCH'', ''Plugin'', ''web_search'', ''联网搜索'', ''[{\"key\": \"provider\", \"type\": \"string\", \"label\": \"搜索源：metaso / tavily\", \"default\": \"metaso\", \"editing\": false, \"selected\": false}, {\"key\": \"description\", \"type\": \"string\", \"label\": \"工具描述\", \"default\": \"联网搜索工具。当用户明确需要联网搜索问题时使用此工具。\", \"editing\": false, \"selected\": false}, {\"key\": \"max_results\", \"type\": \"string\", \"label\": \"返回数量\", \"default\": \"5\", \"editing\": false, \"selected\": false}, {\"key\": \"api_key\", \"type\": \"string\", \"label\": \"apiKey\", \"default\": \"mk-XXXX\", \"editing\": false, \"selected\": false}]'', 80, 1988490863118454785, ''2026-05-11 17:15:35'', 1988490863118454785, ''2026-05-12 10:55:49'')',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------
-- 来源: 202605251426.sql
-- -------------------------------------------------------------
-- 新增呼叫设备工具配置                                                                                                                            
SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_CALL_DEVICE');                                                   
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`,
`update_date`) VALUES (''SYSTEM_PLUGIN_CALL_DEVICE'', ''Plugin'', ''call_device'', ''设备呼叫设备'', ''[]'', 85, 1988490863118454785, ''2026-05-18     
12:00:00'', 1988490863118454785, ''2026-05-18 12:00:00'')',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 更新系统菜单配置，增加联系人管理菜单
UPDATE sys_params
SET param_value = CAST(
    JSON_SET(
        CAST(param_value AS JSON),
        '$.addressBook',
        JSON_OBJECT(
            'name', 'feature.addressBook.name',
            'enabled', FALSE,
            'description', 'feature.addressBook.description'
        )
    ) AS CHAR
)
WHERE param_code = 'system-web.menu'
  AND NOT JSON_CONTAINS_PATH(CAST(param_value AS JSON), 'one', '$.addressBook');

-- 创建设备通讯录表
CREATE TABLE IF NOT EXISTS `ai_device_address_book` (
    `mac_address` VARCHAR(64) NOT NULL COMMENT '本设备MAC地址',
    `target_mac` VARCHAR(64) NOT NULL COMMENT '对方设备MAC地址',
    `alias` VARCHAR(64) DEFAULT NULL COMMENT '别名',
    `has_permission` TINYINT(1) DEFAULT TRUE COMMENT '是否有权限呼叫',
    `creator` BIGINT DEFAULT NULL COMMENT '创建人',
    `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater` BIGINT DEFAULT NULL COMMENT '更新人',
    `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`mac_address`, `target_mac`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备通讯录表';

-- -------------------------------------------------------------
-- 来源: 202606231030.sql
-- -------------------------------------------------------------
-- 更新EdgeTTS供应器增加语速、音调、音量配置
UPDATE `ai_model_provider`
SET fields = '[{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"rate","label":"语速(-100~100)","type":"number"},{"key":"volume","label":"音量(0~100)","type":"number"},{"key":"pitch","label":"音调(-100~100)","type":"number"}]'
WHERE id = 'SYSTEM_TTS_edge';

UPDATE `ai_model_config` SET
`remark` = 'EdgeTTS配置说明：
1. 使用微软Edge TTS服务
2. 支持多种语言和音色
3. 免费使用，无需注册
4. 需要网络连接
5. 输出文件保存在tmp/目录
6. 语速：-100~100，0为正常速度
7. 音量：0~100，50为正常音量
8. 音调：-100~100，0为正常音调' WHERE `id` = 'TTS_EdgeTTS';

-- -------------------------------------------------------------
-- 来源: 202606261131.sql
-- -------------------------------------------------------------
-- 修正、添加Minimax流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_MinimaxStreamTTS';

INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0001', 'TTS_MinimaxStreamTTS', '少女音', 'female-shaonv', '普通话', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0002', 'TTS_MinimaxStreamTTS', '成熟女声', 'female-chengshu', '普通话', NULL, NULL, NULL, NULL, 2, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0003', 'TTS_MinimaxStreamTTS', '霸道少爷', 'badao_shaoye', '普通话', NULL, NULL, NULL, NULL, 3, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0004', 'TTS_MinimaxStreamTTS', '病娇弟弟', 'bingjiao_didi', '普通话', NULL, NULL, NULL, NULL, 4, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0005', 'TTS_MinimaxStreamTTS', '纯真学弟', 'chunzhen_xuedi', '普通话', NULL, NULL, NULL, NULL, 5, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0006', 'TTS_MinimaxStreamTTS', '冷淡学长', 'lengdan_xiongzhang', '普通话', NULL, NULL, NULL, NULL, 6, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0007', 'TTS_MinimaxStreamTTS', '甜美小玲', 'tianxin_xiaoling', '普通话', NULL, NULL, NULL, NULL, 7, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0008', 'TTS_MinimaxStreamTTS', '俏皮萌妹', 'qiaopi_mengmei', '普通话', NULL, NULL, NULL, NULL, 8, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0009', 'TTS_MinimaxStreamTTS', '妩媚御姐', 'wumei_yujie', '普通话', NULL, NULL, NULL, NULL, 9, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0010', 'TTS_MinimaxStreamTTS', '调教学妹', 'diadia_xuemei', '普通话', NULL, NULL, NULL, NULL, 10, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0011', 'TTS_MinimaxStreamTTS', '淡雅学姐', 'danya_xuejie', '普通话', NULL, NULL, NULL, NULL, 11, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0012', 'TTS_MinimaxStreamTTS', 'Santa Claus', 'Santa_Claus', '普通话', NULL, NULL, NULL, NULL, 12, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0013', 'TTS_MinimaxStreamTTS', 'Grinch', 'Grinch', '普通话', NULL, NULL, NULL, NULL, 13, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0014', 'TTS_MinimaxStreamTTS', '专业女主持', 'Cantonese_ProfessionalHost（F)', '粤语', "https://filecdn.minimax.chat/public/84589766-c651-477b-b320-36b89599f953.mp3", NULL, NULL, NULL, 14, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0015', 'TTS_MinimaxStreamTTS', '温柔女声', 'Cantonese_GentleLady', '粤语', "https://filecdn.minimax.chat/public/d391936d-d586-4dab-886c-a2a084a20920.mp3", NULL, NULL, NULL, 15, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0016', 'TTS_MinimaxStreamTTS', '专业男主持', 'Cantonese_ProfessionalHost（M)', '粤语', NULL, NULL, NULL, NULL, 16, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0017', 'TTS_MinimaxStreamTTS', '活泼男声', 'Cantonese_PlayfulMan', '粤语', NULL, NULL, NULL, NULL, 17, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0018', 'TTS_MinimaxStreamTTS', '可爱女孩', 'Cantonese_CuteGirl', '粤语', "https://filecdn.minimax.chat/public/ff96520a-ac12-491d-945e-d6337467eb7d.mp3", NULL, NULL, NULL, 18, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0019', 'TTS_MinimaxStreamTTS', '善良女声', 'Cantonese_KindWoman', '粤语', "https://filecdn.minimax.chat/public/78239a18-5e9c-4538-94f6-2f504c080374.mp3", NULL, NULL, NULL, 19, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0020', 'TTS_MinimaxStreamTTS', 'Crisp News Anchor', 'Cantonese_crisp_news_anchor_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/741a5a4b-f42a-4a9b-ae83-3954d097ab73.mp3', NULL, NULL, NULL, 20, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0021', 'TTS_MinimaxStreamTTS', 'Pro Reporter', 'Cantonese_professional_reporter_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/77afb86d-2cc4-4149-8c2e-e1174fa849d4.mp3', NULL, NULL, NULL, 21, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0022', 'TTS_MinimaxStreamTTS', 'Crisp Reporter', 'Cantonese_crisp_reporter_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/4ad39a61-628e-481c-9d60-bfb7c36bceb8.mp3', NULL, NULL, NULL, 22, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0023', 'TTS_MinimaxStreamTTS', 'Articulate', 'Cantonese_Articulate_commentator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/9346601d-3035-4f9e-9b1c-0e03f30e5eef.mp3', NULL, NULL, NULL, 23, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0024', 'TTS_MinimaxStreamTTS', 'Warm Reporter', 'Cantonese_Warm_Reporter_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/c651050e-d6a5-4653-b09e-5177bdc8b04c.mp3', NULL, NULL, NULL, 24, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0025', 'TTS_MinimaxStreamTTS', 'Energetic', 'Cantonese_energetic_commentator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/1fd1c461-71da-450d-91bb-45f819249b44.mp3', NULL, NULL, NULL, 25, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0026', 'TTS_MinimaxStreamTTS', 'Objective Narrator', 'Cantonese_objective_narrator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/463c5a68-a7b5-4fe9-85b6-d494dca74abb.mp3', NULL, NULL, NULL, 26, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0027', 'TTS_MinimaxStreamTTS', '沙哑男声', 'Cantonese_Narrator', '粤语', 'https://filecdn.minimax.chat/public/22e29cb0-0f5a-443a-9fa9-a32dabd55cf9.mp3', NULL, NULL, NULL, 27, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0028', 'TTS_MinimaxStreamTTS', 'News Anchor', 'Cantonese_news_anchor_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/59b9ba49-47d4-48f1-b207-09c0e0769a1b.mp3', NULL, NULL, NULL, 28, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0029', 'TTS_MinimaxStreamTTS', '渊博学者', 'Cantonese_WiselProfessor', '粤语', 'https://filecdn.minimax.chat/public/8de234c4-64a7-4539-a316-c3b43ee1d0a9.mp3', NULL, NULL, NULL, 29, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0030', 'TTS_MinimaxStreamTTS', 'Resonant Host', 'Cantonese_resonant_host_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/ec8fc0ce-6657-4c49-9bf0-3953a15046ec.mp3', NULL, NULL, NULL, 30, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0031', 'TTS_MinimaxStreamTTS', '冷漠员工', 'Cantonese_IndifferentStaff', '粤语', 'https://filecdn.minimax.chat/public/9686682c-3fc8-45f0-bd88-2a4692e1f63e.mp3', NULL, NULL, NULL, 31, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0032', 'TTS_MinimaxStreamTTS', 'Male News Anchor', 'Cantonese_Male_news_anchor_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/2055ee8b-fb25-424c-b8cb-e2baf971e520.mp3', NULL, NULL, NULL, 32, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0033', 'TTS_MinimaxStreamTTS', 'History Narrator', 'Cantonese_casual_narrator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/c170f9e4-145d-4331-9910-1c3a0e6bbc3a.mp3', NULL, NULL, NULL, 33, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0034', 'TTS_MinimaxStreamTTS', 'Steady Reporter', 'Cantonese_Steady_reporter_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/381cfee2-772d-4a73-b30c-7914aec05771.mp3', NULL, NULL, NULL, 34, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0035', 'TTS_MinimaxStreamTTS', 'Serious Commentator', 'Cantonese_serious_commentator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/57335c8a-32ea-475f-a198-b0de7fa1b126.mp3', NULL, NULL, NULL, 35, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0036', 'TTS_MinimaxStreamTTS', 'Podcast Host', 'Cantonese_podcast_host_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/048b617f-e1f8-422c-89fb-fdbc6e303675.mp3', NULL, NULL, NULL, 36, NULL, NULL, NULL, NULL);
INSERT INTO `ai_tts_voice` VALUES ('TTS_MinimaxStreamTTS_0037', 'TTS_MinimaxStreamTTS', 'Obj commentator', 'Cantonese_Objective_commentator_vv2', '粤语', 'https://cdn.hailuoai.video/open-hailuo-video-web/public_assets/a8f55e44-b726-4ba5-815a-f1b515ba57ef.mp3', NULL, NULL, NULL, 37, NULL, NULL, NULL, NULL);

-- -------------------------------------------------------------
-- 来源: 202607011405.sql
-- -------------------------------------------------------------
-- Add language configuration for local FunASR ASR.
UPDATE `ai_model_provider`
SET `fields` = '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"language","label":"识别语言","type":"string","default":"auto"}]'
WHERE `id` = 'SYSTEM_ASR_FunASR';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.language', 'auto')
WHERE `id` = 'ASR_FunASR'
AND JSON_EXTRACT(`config_json`, '$.language') IS NULL;

-- Update the FunASR local model configuration description to mention the language option.
UPDATE `ai_model_config`
SET `remark` = 'FunASR本地模型配置说明：
1. 需要下载模型文件到xiaozhi-server/models/SenseVoiceSmall目录
2. 支持中日韩粤语音识别
3. 本地推理，无需网络连接
4. 待识别文件保存在tmp/目录
5. “识别语言”字段控制识别语种：auto = 自动检测；如需限定只识别中文可设为 zh（en=英语、ja=日语、ko=韩语、yue=粤语）。'
WHERE `id` = 'ASR_FunASR';

-- -------------------------------------------------------------
-- 来源: 202607071530.sql
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `ai_agent_snapshot` (
    `id` VARCHAR(32) NOT NULL COMMENT '快照ID',
    `agent_id` VARCHAR(32) NOT NULL COMMENT '智能体ID',
    `user_id` BIGINT DEFAULT NULL COMMENT '所属用户ID',
    `version_no` INT UNSIGNED NOT NULL COMMENT '版本号',
    `snapshot_data` JSON NOT NULL DEFAULT (JSON_OBJECT()) COMMENT '快照数据',
    `changed_fields` JSON DEFAULT NULL COMMENT '变更字段',
    `source` VARCHAR(32) DEFAULT 'config' COMMENT '快照来源',
    `restore_from_snapshot_id` VARCHAR(32) DEFAULT NULL COMMENT '恢复来源快照ID',
    `restore_from_version_no` INT UNSIGNED DEFAULT NULL COMMENT '恢复来源版本号',
    `creator` BIGINT DEFAULT NULL COMMENT '创建者',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_agent_version` (`agent_id`, `version_no`),
    INDEX `idx_agent_created_at` (`agent_id`, `created_at`),
    INDEX `idx_snapshot_user_created_at` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置快照表';

-- -------------------------------------------------------------
-- 来源: 202607101200.sql
-- -------------------------------------------------------------

ALTER TABLE `ai_agent_snapshot`
    ADD COLUMN `redaction_version` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '快照脱敏规则版本' AFTER `created_at`,
    ADD INDEX `idx_snapshot_redaction_version_id` (`redaction_version`, `id`);

-- -------------------------------------------------------------
-- 来源: 202607290930.sql
-- -------------------------------------------------------------

-- 插入新的 hass_state 插件记录（合并 get_state 的配置字段）
INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields,
                               sort, creator, create_date, updater, update_date)
VALUES ('SYSTEM_PLUGIN_HA_STATE',
        'Plugin',
        'hass_state',
        'HomeAssistant设备控制',
        JSON_ARRAY(
                JSON_OBJECT(
                        'key', 'base_url',
                        'type', 'string',
                        'label', 'HA 服务器地址',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.base_url')
                ),
                JSON_OBJECT(
                        'key', 'api_key',
                        'type', 'string',
                        'label', 'HA API 访问令牌',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.api_key')
                ),
                JSON_OBJECT(
                        'key', 'devices',
                        'type', 'array',
                        'label', '设备列表（名称,实体ID;…）',
                        'default',
                        (SELECT param_value FROM sys_params WHERE param_code = 'plugins.home_assistant.devices')
                )
        ),
        50, 0, NOW(), 0, NOW());

-- 迁移已配置的 agent：把指向 HA_GET_STATE 的改成 HA_STATE（保留参数）
UPDATE ai_agent_plugin_mapping
SET plugin_id = 'SYSTEM_PLUGIN_HA_STATE'
WHERE plugin_id = 'SYSTEM_PLUGIN_HA_GET_STATE';

-- HA_SET_STATE 本来就没有配置字段（fields=[]），直接删除其 mapping
DELETE FROM ai_agent_plugin_mapping
WHERE plugin_id = 'SYSTEM_PLUGIN_HA_SET_STATE';

-- 删除旧的插件定义
DELETE FROM ai_model_provider
WHERE id IN ('SYSTEM_PLUGIN_HA_GET_STATE', 'SYSTEM_PLUGIN_HA_SET_STATE');

-- -------------------------------------------------------------
-- 来源: 202608061030.sql
-- -------------------------------------------------------------
UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'deepseek-v4-flash')
WHERE `id` = 'LLM_DeepSeekLLM'
  AND JSON_EXTRACT(`config_json`, '$.model_name') = 'deepseek-chat';

-- -------------------------------------------------------------
-- 来源: 202608061800.sql
-- -------------------------------------------------------------
UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'doubao-seed-2-0-lite-260215')
WHERE `id` = 'LLM_DoubaoLLM'
  AND JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.model_name')) IN (
    'doubao-1-5-pro-32k-250115'
  );

UPDATE `ai_model_config`
SET `remark` = REPLACE(
    REPLACE(
        `remark`,
        '开通Doubao-1.5-pro服务',
        '开通 Doubao-Seed-2.0-Lite 服务'
    ),
    '当前建议使用doubao-1-5-pro-32k-250115',
    '当前建议使用 doubao-seed-2-0-lite-260215'
)
WHERE `id` = 'LLM_DoubaoLLM'
  AND (
    `remark` LIKE '%Doubao-1.5-pro%'
    OR `remark` LIKE '%doubao-1-5-pro-32k-250115%'
  );

-- -------------------------------------------------------------
-- 来源: 202608131030.sql
-- -------------------------------------------------------------
UPDATE `sys_params`
SET `param_value` = '15'
WHERE `param_code` = 'tts_timeout'
  AND `param_value` = '10';

-- -------------------------------------------------------------
-- 来源: 202609021000.sql
-- -------------------------------------------------------------
-- 阿里百炼流式 TTS 支持业务空间 WebSocket 地址

UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY(
    JSON_OBJECT('key', 'api_key', 'type', 'string', 'label', 'API密钥'),
    JSON_OBJECT(
        'key', 'ws_url',
        'type', 'string',
        'label', 'WebSocket地址（含Workspace ID）',
        'default', 'wss://dashscope.aliyuncs.com/api-ws/v1/inference/'
    ),
    JSON_OBJECT('key', 'output_dir', 'type', 'string', 'label', '输出目录'),
    JSON_OBJECT('key', 'model', 'type', 'string', 'label', '模型'),
    JSON_OBJECT('key', 'voice', 'type', 'string', 'label', '音色'),
    JSON_OBJECT('key', 'format', 'type', 'string', 'label', '音频格式'),
    JSON_OBJECT('key', 'sample_rate', 'type', 'number', 'label', '采样率'),
    JSON_OBJECT('key', 'volume', 'type', 'number', 'label', '音量'),
    JSON_OBJECT('key', 'rate', 'type', 'number', 'label', '语速'),
    JSON_OBJECT('key', 'pitch', 'type', 'number', 'label', '音调')
)
WHERE `id` = 'SYSTEM_TTS_AliBLStreamTTS';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(
    `config_json`,
    '$.ws_url',
    COALESCE(
        NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.ws_url')), ''),
        'wss://dashscope.aliyuncs.com/api-ws/v1/inference/'
    )
)
WHERE `id` = 'TTS_AliBLStreamTTS';

UPDATE `ai_model_config`
SET `remark` = '阿里百炼流式 TTS 配置说明：
1. API密钥填写当前业务空间可用的 DashScope API Key
2. 公有模式可使用 wss://dashscope.aliyuncs.com/api-ws/v1/inference/
3. 华北2（北京）业务空间填写 wss://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference
4. 新加坡业务空间填写 wss://<WorkspaceId>.ap-southeast-1.maas.aliyuncs.com/api-ws/v1/inference
5. 将 <WorkspaceId> 替换为真实业务空间 ID；仅支持阿里云官方 WSS 推理地址
6. 支持 CosyVoice 流式合成及音量、语速、音调配置'
WHERE `id` = 'TTS_AliBLStreamTTS';

-- -------------------------------------------------------------
-- 来源: 202609172100.sql
-- -------------------------------------------------------------
-- 联网搜索插件新增Serply搜索源

UPDATE `ai_model_provider`
SET `fields` = JSON_SET(
    `fields`,
    '$[0].label',
    '搜索源：metaso / tavily / serply'
)
WHERE `id` = 'SYSTEM_PLUGIN_WEB_SEARCH';

