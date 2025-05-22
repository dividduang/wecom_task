#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.plugin.wecom_task.model.model_wecom_task import WecomTask


class CRUDWecomTask(CRUDPlus[WecomTask]):
    async def create_task(
        self,
        db: AsyncSession,
        name: str,
        webhook_url: str,
        message_type: str,
        message_content: str,
        cron_expression: str,
        next_run_time: Optional[datetime] = None,
        status: int = 1,
        file_path: Optional[str] = None
    ) -> WecomTask:
        """
        创建企业微信任务

        :param db: 数据库会话
        :param name: 任务名称
        :param webhook_url: Webhook地址
        :param message_type: 消息类型
        :param message_content: 消息内容
        :param cron_expression: Cron表达式
        :param next_run_time: 下次运行时间
        :param status: 状态
        :param file_path: 文件或图片路径
        :return: 创建的任务
        """
        task = WecomTask(
            name=name,
            webhook_url=webhook_url,
            message_content=message_content,
            cron_expression=cron_expression,
            message_type=message_type,
            next_run_time=next_run_time,
            status=status,
            file_path=file_path
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    async def update_task(
        self,
        db: AsyncSession,
        task_id: int,
        update_data: Dict[str, Any]
    ) -> Optional[WecomTask]:
        """
        更新企业微信任务

        :param db: 数据库会话
        :param task_id: 任务ID
        :param update_data: 更新数据
        :return: 更新后的任务
        """
        task = await self.select_model_by_column(db, id=task_id)
        if not task:
            return None

        for key, value in update_data.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)

        await db.commit()
        await db.refresh(task)
        return task

    async def get_all_active_tasks(self, db: AsyncSession) -> List[WecomTask]:
        """
        获取所有活动状态的任务

        :param db: 数据库会话
        :return: 任务列表
        """
        stmt = select(self.model).where(self.model.status == 1)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_by_status(self, db: AsyncSession, status: int) -> List[WecomTask]:
        """
        根据状态获取任务

        :param db: 数据库会话
        :param status: 状态
        :return: 任务列表
        """
        stmt = select(self.model).where(self.model.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_next_run_time(
        self,
        db: AsyncSession,
        task_id: int,
        next_run_time: datetime
    ) -> bool:
        """
        更新任务的下次运行时间

        :param db: 数据库会话
        :param task_id: 任务ID
        :param next_run_time: 下次运行时间
        :return: 是否更新成功
        """
        stmt = (
            update(self.model)
            .where(self.model.id == task_id)
            .values(next_run_time=next_run_time)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    async def get_due_tasks(self, db: AsyncSession, current_time: datetime) -> List[WecomTask]:
        """
        获取到期的任务

        :param db: 数据库会话
        :param current_time: 当前时间
        :return: 到期的任务列表
        """
        stmt = select(self.model).where(
            and_(
                self.model.status == 1,
                self.model.next_run_time <= current_time
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


wecom_task_dao: CRUDWecomTask = CRUDWecomTask(WecomTask)
