#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime
import threading
from sqlalchemy import create_engine, select, update, and_
from sqlalchemy.orm import sessionmaker, Session

# 使用插件自己的Celery实例
from backend.plugin.wecom_task.celery import get_celery_app
from backend.plugin.wecom_task.service.schedule_utils import calculate_next_run_time
from backend.plugin.wecom_task.service.wecom_webhook import WechatWorkWebhook
from backend.plugin.wecom_task.conf import task_settings
from backend.plugin.wecom_task.model.model_wecom_task import WecomTask
from backend.core.conf import settings

logger = logging.getLogger(__name__)

# 创建同步数据库连接
def create_sync_engine():
    """创建同步数据库引擎"""
    database_url = (
        f"mysql+pymysql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}"
        f"@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_SCHEMA}"
        f"?charset={settings.DATABASE_CHARSET}"
    )
    return create_engine(
        database_url,
        echo=settings.DATABASE_ECHO,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

sync_engine = create_sync_engine()
SyncSession = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)


def get_due_tasks_sync(current_time: datetime) -> list[WecomTask]:
    """同步获取到期的任务"""
    with SyncSession() as db:
        stmt = select(WecomTask).where(
            and_(
                WecomTask.status == 1,
                WecomTask.next_run_time <= current_time
            )
        )
        result = db.execute(stmt)
        return list(result.scalars().all())


def get_task_by_id_sync(task_id: int) -> WecomTask | None:
    """同步根据ID获取任务"""
    with SyncSession() as db:
        stmt = select(WecomTask).where(WecomTask.id == task_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()


def update_next_run_time_sync(task_id: int, next_run_time: datetime) -> bool:
    """同步更新任务的下次运行时间"""
    with SyncSession() as db:
        stmt = (
            update(WecomTask)
            .where(WecomTask.id == task_id)
            .values(next_run_time=next_run_time)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0


@get_celery_app().task(name='wecom_check_due_tasks')
def check_due_tasks() -> dict:
    """
    检查是否有到期的企业微信任务需要执行
    """
    logger.info("开始检查到期企业微信任务")
    try:
        current_time = datetime.now()
        logger.info(f"检查到期企业微信任务: {current_time}")
        due_tasks = get_due_tasks_sync(current_time)
        logger.info(f"找到 {len(due_tasks)} 个到期企业微信任务")

        for task in due_tasks:
            try:
                result = execute_task_sync(task)
                logger.info(f"执行企业微信任务成功: {task.name} (ID: {task.id})")
                next_run_time = calculate_next_run_time(task.cron_expression)
                if next_run_time:
                    update_next_run_time_sync(task.id, next_run_time)
                    logger.info(f"更新企业微信任务下次运行时间: {task.name} (ID: {task.id}) -> {next_run_time}")
            except Exception as e:
                logger.error(f"执行企业微信任务失败: {task.name} (ID: {task.id}) - {str(e)}")

        return {"success": True, "message": "检查到期企业微信任务完成"}
    except Exception as e:
        logger.error(f"检查到期企业微信任务失败: {str(e)}")
        return {"success": False, "message": f"检查到期企业微信任务失败: {str(e)}"}

@get_celery_app().task(name='wecom_execute_task')
def execute_wecom_task(task_id: int) -> dict:
    """
    执行指定的企业微信任务
    :param task_id: 任务ID
    :return: 执行结果
    """
    logger.info(f"开始执行企业微信任务: {task_id}")
    try:
        task = get_task_by_id_sync(task_id)
        if not task:
            raise ValueError(f"未找到ID为 {task_id} 的任务")
        result = execute_task_sync(task)
        return result
    except Exception as e:
        logger.error(f"执行企业微信任务失败: {str(e)}")
        return {"success": False, "message": f"执行企业微信任务失败: {str(e)}"}


def execute_task_sync(task: WecomTask) -> dict:
    """
    同步执行企业微信任务
    :param task: 任务对象
    :return: 执行结果
    """
    try:
        webhook = WechatWorkWebhook(task.webhook_url)
        if task.message_type == "text":
            result = webhook.text(task.message_content)
        elif task.message_type == "markdown":
            result = webhook.markdown(task.message_content)
        else:
            result = webhook.text(task.message_content)

        if result.get("errcode") == 0:
            return {
                "success": True,
                "message": "发送成功",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": f"发送失败: {result.get('errmsg', '未知错误')}",
                "data": result
            }
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return {"success": False, "message": f"执行任务失败: {str(e)}"}
