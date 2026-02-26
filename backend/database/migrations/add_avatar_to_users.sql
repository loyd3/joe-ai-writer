-- 用户表增加头像 URL（若已存在可忽略报错）
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) DEFAULT NULL;
