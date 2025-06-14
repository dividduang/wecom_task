#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime

from backend.app.task.celery import celery_app
from backend.database.db import async_db_session
from backend.plugin.wecom_task.crud.crud_wecom_task import wecom_task_dao
from backend.plugin.wecom_task.service.schedule_utils import calculate_next_run_time
from backend.plugin.wecom_task.service.wecom_webhook import WechatWorkWebhook

logger = logging.getLogger(__name__)


@celery_app.task(name='wecom_check_due_tasks')
def check_due_tasks() -> dict:
    """
    检查是否有到期的企业微信任务需要执行
    """
    logger.info("开始检查到期企业微信任务")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_check_due_tasks())
        return result
    except Exception as e:
        logger.error(f"检查到期企业微信任务失败: {str(e)}")
        return {"success": False, "message": f"检查到期企业微信任务失败: {str(e)}"}
    finally:
        loop.close()


async def _check_due_tasks() -> dict:
    """
    异步检查到期任务
    """
    try:
        async with async_db_session() as db:
            # 获取当前时间
            current_time = datetime.now()
            logger.info(f"检查到期企业微信任务: {current_time}")
            
            # 获取到期的任务
            due_tasks = await wecom_task_dao.get_due_tasks(db, current_time)
            logger.info(f"找到 {len(due_tasks)} 个到期企业微信任务")
            
            # 执行每个到期的任务
            for task in due_tasks:
                try:
                    # 执行任务
                    await execute_task(task.id, db)
                    logger.info(f"执行企业微信任务成功: {task.name} (ID: {task.id})")
                    
                    # 更新下次运行时间
                    next_run_time = calculate_next_run_time(task.cron_expression)
                    if next_run_time:
                        await wecom_task_dao.update_next_run_time(db, task.id, next_run_time)
                        logger.info(f"更新企业微信任务下次运行时间: {task.name} (ID: {task.id}) -> {next_run_time}")
                except Exception as e:
                    logger.error(f"执行企业微信任务失败: {task.name} (ID: {task.id}) - {str(e)}")
            
            return {"success": True, "message": "检查到期企业微信任务完成"}
    except Exception as e:
        logger.error(f"检查到期企业微信任务失败: {str(e)}")
        return {"success": False, "message": f"检查到期企业微信任务失败: {str(e)}"}


@celery_app.task(name='wecom_execute_task')
def execute_wecom_task(task_id: int) -> dict:
    """
    执行指定的企业微信任务
    
    :param task_id: 任务ID
    :return: 执行结果
    """
    logger.info(f"开始执行企业微信任务: {task_id}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(execute_task(task_id))
        return result
    except Exception as e:
        logger.error(f"执行企业微信任务失败: {str(e)}")
        return {"success": False, "message": f"执行企业微信任务失败: {str(e)}"}
    finally:
        loop.close()


async def execute_task(task_id: int, db=None) -> dict:
    """
    异步执行任务
    
    :param task_id: 任务ID
    :param db: 数据库会话，如果为None则创建新会话
    :return: 执行结果
    """
    close_db = False
    if db is None:
        db = await async_db_session().__aenter__()
        close_db = True
    
    try:
        # 获取任务
        task = await wecom_task_dao.select_model_by_column(db, id=task_id)
        if not task:
            raise ValueError(f"未找到ID为 {task_id} 的任务")
        
        # 发送消息
        webhook = WechatWorkWebhook(task.webhook_url)
        
        if task.message_type == "text":
            result = webhook.text(task.message_content)
        elif task.message_type == "markdown":
            result = webhook.markdown(task.message_content)
        else:
            # 默认使用文本类型
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
    finally:
        if close_db:
            await db.__aexit__(None, None, None)
