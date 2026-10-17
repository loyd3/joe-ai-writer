-- 智能体运行表（幂等手工迁移参考；启动时 Base.metadata.create_all 会自动建表）
-- 项目智能体：持久化任务 / 步骤事件 / 暂存修改集 / 租约与幂等键

CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID',
    scope VARCHAR(20) NOT NULL DEFAULT 'project' COMMENT 'project | system（预留）',
    project_id INT NULL COMMENT '项目域运行的所属项目',
    user_id INT NOT NULL COMMENT '发起用户',
    conversation_id VARCHAR(36) NOT NULL COMMENT '会话 id，同会话多个 run 聚合',
    instruction TEXT NOT NULL COMMENT '用户指令',
    status VARCHAR(20) NOT NULL DEFAULT 'queued'
      COMMENT 'queued|running|proposed|completed|failed|cancelled|applied|reverted',
    answer TEXT NULL COMMENT 'finish 总结答复',
    error TEXT NULL,
    changes JSON NULL COMMENT '暂存修改集（ChangeSet）',
    events JSON NULL COMMENT '步骤/事件流水 [{sequence,type,message}]',
    messages JSON NULL COMMENT '对话记录 [{role,content,step}]',
    model_config JSON NULL COMMENT '创建时模型配置快照',
    input_versions JSON NULL COMMENT '执行基线快照（文档/设定 updated_at）',
    idempotency_key VARCHAR(64) NULL COMMENT '幂等键，唯一',
    lease_owner VARCHAR(36) NULL COMMENT '工作器租约持有者',
    lease_until DATETIME NULL COMMENT '租约到期时间，过期可被接管',
    heartbeat_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_agent_runs_idem (idempotency_key),
    INDEX ix_agent_runs_project (project_id),
    INDEX ix_agent_runs_conversation (conversation_id),
    INDEX ix_agent_runs_status_lease (status, lease_until),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='智能体运行（任务/事件/修改集/租约）';
