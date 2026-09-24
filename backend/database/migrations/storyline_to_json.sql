-- 项目设定：storyline 从 TEXT 升级为 JSON（兼容旧纯文本）
-- MySQL 8+

USE joe_writer;

-- 将非 JSON 的旧故事线文本包成 { summary, stages }
UPDATE ai_memories
SET storyline = JSON_OBJECT('summary', IFNULL(storyline, ''), 'stages', JSON_ARRAY())
WHERE storyline IS NOT NULL
  AND storyline != ''
  AND JSON_VALID(storyline) = 0;

UPDATE ai_memories
SET storyline = JSON_OBJECT('summary', '', 'stages', JSON_ARRAY())
WHERE storyline IS NULL OR storyline = '';

ALTER TABLE ai_memories
  MODIFY COLUMN storyline JSON NULL;
