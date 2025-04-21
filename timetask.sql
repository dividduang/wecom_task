CREATE TABLE wecom_task (
    id INT AUTO_INCREMENT COMMENT '主键 ID' PRIMARY KEY,
    uuid VARCHAR(50) NOT NULL COMMENT 'UUID',
    name VARCHAR(100) NOT NULL COMMENT '任务名称',
    webhook_url VARCHAR(255) NOT NULL COMMENT '企业微信群机器人Webhook地址',
    message_type VARCHAR(50) NOT NULL DEFAULT 'text' COMMENT '消息类型(text, markdown, image等)',
    message_content TEXT NOT NULL COMMENT '消息内容',
    cron_expression VARCHAR(100) NOT NULL COMMENT 'Cron表达式',
    next_run_time DATETIME COMMENT '下次运行时间',
    status TINYINT(1) NOT NULL DEFAULT 1 COMMENT '状态(0停用 1正常)',
    created_time DATETIME NOT NULL COMMENT '创建时间',
    updated_time DATETIME COMMENT '更新时间',
    CONSTRAINT uuid UNIQUE (uuid)
) COMMENT '企业微信群机器人任务表';

CREATE INDEX ix_wecom_task_id ON wecom_task (id);
