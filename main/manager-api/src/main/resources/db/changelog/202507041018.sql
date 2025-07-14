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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体声纹表'