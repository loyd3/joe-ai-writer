-- 文风智能体：项目级 → 用户级（幂等手工迁移参考；启动时 main._ensure_style_agents_user_scoped 也会跑）
-- 1) 加 user_id / source
-- 2) 从 projects.owner_id 回填
-- 3) 删除 project_id

ALTER TABLE writing_style_agents
  ADD COLUMN IF NOT EXISTS user_id INT NULL COMMENT '所属用户' AFTER id;

ALTER TABLE writing_style_agents
  ADD COLUMN IF NOT EXISTS source VARCHAR(32) NULL DEFAULT 'manual'
  COMMENT 'preset|manual|extract' AFTER is_default;

UPDATE writing_style_agents w
JOIN projects p ON w.project_id = p.id
SET w.user_id = p.owner_id
WHERE w.user_id IS NULL;

DELETE FROM writing_style_agents WHERE user_id IS NULL;

-- 同用户同名去重（保留最小 id）
DELETE w1 FROM writing_style_agents w1
INNER JOIN writing_style_agents w2
  ON w1.user_id = w2.user_id AND w1.name = w2.name AND w1.id > w2.id;

ALTER TABLE writing_style_agents MODIFY COLUMN user_id INT NOT NULL;

-- 以下按实际外键名调整；失败可忽略
-- ALTER TABLE writing_style_agents DROP FOREIGN KEY writing_style_agents_ibfk_1;
-- ALTER TABLE writing_style_agents DROP COLUMN project_id;
-- ALTER TABLE writing_style_agents ADD INDEX idx_style_agent_user (user_id);
-- ALTER TABLE writing_style_agents ADD CONSTRAINT fk_style_agent_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
