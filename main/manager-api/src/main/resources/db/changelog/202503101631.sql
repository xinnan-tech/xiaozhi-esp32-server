-- 给用户表添加一个创建者
ALTER TABLE sys_user ADD COLUMN creator BIGINT COMMENT '创建者';