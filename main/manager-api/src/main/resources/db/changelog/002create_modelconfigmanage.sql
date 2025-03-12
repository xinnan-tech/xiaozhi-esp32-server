-- 1. 模块表（存储模型模块元数据）
CREATE TABLE `model_modules` (
     `module_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
     `module_type` VARCHAR(50) NOT NULL COMMENT '模块类型（如"Memory"）',
     `display_name` VARCHAR(50) NOT NULL COMMENT '展示名称（如"记忆模块"）',
     `description` VARCHAR(500) DEFAULT NULL COMMENT '模块描述',
     `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1启用 0禁用',
     `creator` BIGINT COMMENT '创建者',
     `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
     `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
     UNIQUE KEY `uk_module_type` (`module_type`)
) COMMENT '模型模块注册表';

-- 2. 平台表（存储模块下的具体平台（provideType））
CREATE TABLE `model_platforms` (
   `platform_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
   `module_id` BIGINT NOT NULL COMMENT '所属模块ID',
   `provide_type` VARCHAR(50) NOT NULL COMMENT '平台标识（如DoubaoLLM）',
   `display_name` VARCHAR(50) NOT NULL COMMENT '展示名称（如"豆包大模型"）',
   `description` VARCHAR(500) DEFAULT NULL COMMENT '平台描述',
   `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1启用 0禁用',
   `creator` BIGINT COMMENT '创建者',
   `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
   `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
   UNIQUE KEY `uk_module_platform` (`module_id`, `provide_type`)
) COMMENT '模型平台注册表';

-- 3. 参数模板表（存储各平台的参数规范）
CREATE TABLE `model_param_templates` (
     `param_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
     `platform_id` BIGINT NOT NULL COMMENT '所属平台ID',
     `param_key` VARCHAR(50) NOT NULL COMMENT '参数键（如api_key）',
     `param_name` VARCHAR(50) NOT NULL COMMENT '参数名称（如"API密钥"）',
     `param_type` ENUM('string', 'int', 'bool', 'secret') NOT NULL COMMENT '参数类型（secret表示敏感字段）',
     `is_required` TINYINT NOT NULL DEFAULT 1 COMMENT '是否必填',
     `default_value` JSON COMMENT '默认值',
     `description` TEXT COMMENT '参数说明',
     `creator` BIGINT COMMENT '创建者',
     `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
     `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
     UNIQUE KEY `uk_platform_param` (`platform_id`, `param_key`)
) COMMENT '模型参数模板表';


-- 4. 配置实例表（存储实际生效的配置）
CREATE TABLE `model_configurations` (
    `config_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `user_id` BIGINT COMMENT '用户ID（scope为user时必填）',
    `module_id` BIGINT NOT NULL COMMENT '模块ID',
    `platform_id` BIGINT NOT NULL COMMENT '平台ID',
    `param_values` JSON NOT NULL COMMENT '参数值（json结构，敏感字段加密存储）',
    `生效状态` TINYINT NOT NULL DEFAULT 1 COMMENT '1生效 0禁用',
    `is_default` TINYINT NOT NULL DEFAULT 0 COMMENT '是否默认配置',
    `creator` BIGINT COMMENT '创建者',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    UNIQUE KEY `uk_scope_user_module` (`user_id`, `module_id`)
) COMMENT '模型配置实例表';


-- 智能体表
CREATE TABLE `agent` (
     `agent_id` BIGINT AUTO_INCREMENT PRIMARY KEY,
     `user_id` BIGINT NOT NULL COMMENT '用户ID，关联sys_user表的id字段',
     `agent_nickname` VARCHAR(50) NOT NULL COMMENT '助手昵称',
     `language_preference` VARCHAR(20) COMMENT '语言偏好，如"zh-CN", "en-US"等',
     `role_introduction` TEXT COMMENT '角色介绍（format）',
     `config_id` BIGINT COMMENT '关联model_configurations表中的config_id字段，用于获取智能体的配置',
     `memory` TEXT COMMENT '记忆体，存储智能体的相关记忆信息',
     `creator` BIGINT COMMENT '创建者',
     `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
     `updated_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
     KEY `idx_user_id` (`user_id`)
) COMMENT '智能体表';

