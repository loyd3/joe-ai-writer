-- 为 users 表增加主题字段（已有数据库执行此迁移，仅需执行一次）
USE aiwriter;

ALTER TABLE users ADD COLUMN theme_preset VARCHAR(32) DEFAULT NULL;
ALTER TABLE users ADD COLUMN theme_custom_color VARCHAR(32) DEFAULT NULL;
