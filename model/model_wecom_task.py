#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key
from backend.database.db import uuid4_str
from backend.utils.timezone import timezone


class WecomTask(DataClassBase):
    """企业微信群机器人任务表"""

    __tablename__ = 'wecom_task'

    id: Mapped[id_key] = mapped_column(init=False)
    uuid: Mapped[str] = mapped_column(String(50), init=False, default_factory=uuid4_str, unique=True)
    name: Mapped[str] = mapped_column(String(100), comment='任务名称')
    webhook_url: Mapped[str] = mapped_column(String(255), comment='企业微信群机器人Webhook地址')
    message_content: Mapped[str] = mapped_column(Text, comment='消息内容')
    cron_expression: Mapped[str] = mapped_column(String(100), comment='Cron表达式')
    message_type: Mapped[str] = mapped_column(String(50), default='text', comment='消息类型(text, markdown, image等)')
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='文件或图片路径')
    next_run_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, comment='下次运行时间')
    status: Mapped[int] = mapped_column(default=1, comment='状态(0停用 1正常)')
    created_time: Mapped[datetime] = mapped_column(init=False, default_factory=timezone.now, comment='创建时间')
    updated_time: Mapped[datetime | None] = mapped_column(init=False, onupdate=timezone.now, comment='更新时间')
