CREATE TABLE sys_integration_credential (
  id varchar(32) NOT NULL COMMENT '凭据公开标识',
  name varchar(100) NOT NULL COMMENT '凭据名称',
  subject varchar(32) NOT NULL COMMENT '独立审计主体',
  owner_user_id bigint NOT NULL COMMENT '可操作资源所属用户',
  token_hash char(64) NOT NULL COMMENT 'SHA-256 凭据摘要',
  enabled tinyint NOT NULL DEFAULT 1 COMMENT '是否可用',
  expires_at datetime NULL COMMENT '可选过期时间',
  last_used_at datetime NULL COMMENT '最后使用时间',
  revoked_at datetime NULL COMMENT '撤销时间',
  creator bigint COMMENT '创建者',
  create_date datetime NOT NULL COMMENT '创建时间',
  updater bigint COMMENT '更新者',
  update_date datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_integration_credential_token_hash (token_hash),
  KEY idx_integration_credential_owner (owner_user_id),
  KEY idx_integration_credential_subject_enabled (subject, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='服务端集成凭据';
