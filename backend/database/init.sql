-- =============================================================================
-- 墨心 · 数据库初始化脚本
-- =============================================================================
-- 库名: joe_writer（与 docker-compose MYSQL_DATABASE 一致）
-- 字符集: utf8mb4 / utf8mb4_unicode_ci
--
-- 表清单与职责（与 app/models/models.py 对照）
-- ---------------------------------------------------------------------------
-- users                 用户账号、主题、头像
-- projects              创作项目
-- documents             块编辑器文档树
-- ai_memories           项目设定 1:1（大纲/角色/世界观等）
-- writing_style_agents  用户级文风智能体
-- ai_interactions       文档 AI 交互历史
-- system_configs        系统键值配置
-- saved_brainstorms     用户收藏脑洞
--
-- 以下表主要由 SQLAlchemy create_all 创建，本脚本未建：
--   templates, document_versions, articles, article_chapters, article_outlines
-- 增量变更见 database/migrations/*.sql（如 avatar_url、storyline JSON、文风表）
-- =============================================================================

CREATE DATABASE IF NOT EXISTS joe_writer
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE joe_writer;

-- ============================================
-- users：用户账号
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户 ID',
    email VARCHAR(255) UNIQUE NOT NULL COMMENT '登录邮箱',
    username VARCHAR(255) UNIQUE NOT NULL COMMENT '用户名',
    hashed_password VARCHAR(255) NOT NULL COMMENT '密码哈希',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    theme_preset VARCHAR(32) DEFAULT NULL COMMENT '主题预设 coffee|teal|indigo|custom',
    theme_custom_color VARCHAR(32) DEFAULT NULL COMMENT '自定义主题色，如 #3E4BC4',
    -- avatar_url 由 migrations/add_avatar_to_users.sql 或启动时 _ensure_avatar_column 追加
    INDEX idx_email (email),
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户账号与偏好';

-- ============================================
-- projects：创作项目（归属用户）
-- ============================================
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '项目 ID',
    title VARCHAR(255) NOT NULL COMMENT '项目标题',
    description TEXT COMMENT '项目简介',
    owner_id INT NOT NULL COMMENT '所有者 users.id',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title),
    INDEX idx_owner (owner_id),
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='创作项目容器';

-- ============================================
-- documents：块编辑器文档（可树形父子）
-- content: [{id,type,content,props?}, ...]
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '文档 ID',
    title VARCHAR(255) NOT NULL COMMENT '文档标题',
    content JSON DEFAULT ('[]') COMMENT '块编辑器 JSON 正文',
    project_id INT NOT NULL COMMENT '所属项目',
    parent_id INT DEFAULT NULL COMMENT '父文档；根文档为 NULL',
    order_index INT DEFAULT 0 COMMENT '同级排序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project (project_id),
    INDEX idx_parent (parent_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES documents(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='项目文档（块结构）';

-- ============================================
-- ai_memories：项目设定（每项目一行）
-- 注入 AI 写作上下文；writing_style 为兼容旧自由文本
-- ============================================
CREATE TABLE IF NOT EXISTS ai_memories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE COMMENT '对应 projects.id，1:1',
    outline JSON DEFAULT ('[]') COMMENT '大纲 [{title,description}]',
    storyline JSON DEFAULT NULL COMMENT '{summary,stages:[{title,summary}]}',
    characters JSON DEFAULT ('[]') COMMENT '角色卡数组',
    world_building JSON DEFAULT ('{}') COMMENT '{categories:[{name,items}]}',
    writing_style TEXT COMMENT '旧版自由文风文本',
    key_points JSON DEFAULT ('[]') COMMENT '关键情节 [{title,summary}]',
    notes TEXT COMMENT '其它备注约束',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='项目级 AI 设定/记忆';

-- ============================================
-- writing_style_agents：用户级文风智能体（跨项目）
-- config: tone/pov/pace/sentence/diction/.../custom_text/samples
-- ============================================
CREATE TABLE IF NOT EXISTS writing_style_agents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '所属用户',
    name VARCHAR(100) NOT NULL COMMENT '智能体名称',
    description TEXT COMMENT '一句话定位',
    preset_key VARCHAR(64) DEFAULT NULL COMMENT '内置预设 key；手建/提炼为空',
    config JSON COMMENT '结构化文风参数',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否用户默认文风',
    source VARCHAR(32) DEFAULT 'manual' COMMENT 'preset|manual|extract',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_style_agent_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户级文风智能体（写作 prompt 注入）';

-- ============================================
-- ai_interactions：文档 AI 交互流水
-- ============================================
CREATE TABLE IF NOT EXISTS ai_interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL COMMENT '关联文档',
    interaction_type VARCHAR(50) NOT NULL COMMENT '如 guide/revise/polish/chat',
    user_input TEXT NOT NULL COMMENT '用户输入或选区摘要',
    ai_response TEXT NOT NULL COMMENT '模型回复',
    context_used JSON DEFAULT ('{}') COMMENT '上下文标记如 memory_used',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document (document_id),
    INDEX idx_type (interaction_type),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='文档级 AI 调用历史';

-- ============================================
-- system_configs：全局键值配置
-- ============================================
CREATE TABLE IF NOT EXISTS system_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL COMMENT '配置键，如 ai_provider',
    config_value TEXT COMMENT '配置值，多为 JSON 字符串',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='系统配置 KV';

-- ============================================
-- saved_brainstorms：用户收藏脑洞
-- ============================================
CREATE TABLE IF NOT EXISTS saved_brainstorms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '收藏者',
    title VARCHAR(255) NOT NULL COMMENT '脑洞标题',
    category VARCHAR(64) DEFAULT '自定义' COMMENT '分类',
    concept TEXT NOT NULL COMMENT '概念正文',
    source VARCHAR(32) DEFAULT 'manual' COMMENT 'manual|trending|random|hot',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户收藏的脑洞';

-- ============================================
-- 默认系统配置种子
-- ============================================
INSERT INTO system_configs (config_key, config_value) VALUES
('ai_provider', '{"value": "deepseek"}'),
('default_model', '{"value": "deepseek-chat"}')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

SHOW TABLES;
