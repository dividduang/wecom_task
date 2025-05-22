#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from datetime import datetime

# 使用插件自己的Celery实例
from backend.plugin.wecom_task.celery import celery_app
from backend.plugin.wecom_task.service.schedule_utils import calculate_next_run_time
from backend.plugin.wecom_task.wecom_func import WechatWorkWebhook

logger = logging.getLogger(__name__)


@celery_app.task(name='wecom_check_due_tasks')
def check_due_tasks() -> dict:
    """
    检查是否有到期的企业微信任务需要执行
    每分钟执行一次，检查数据库中next_run_time小于等于当前时间的任务
    """
    logger.info("开始检查到期企业微信任务")

    # 使用同步方式检查到期任务
    try:
        # 获取当前时间
        current_time = datetime.now()
        logger.info(f"检查到期企业微信任务: {current_time}")

        # 使用SQLAlchemy会话查询数据库
        from sqlalchemy import create_engine, select, and_
        from sqlalchemy.orm import sessionmaker
        from backend.core.conf import settings
        from backend.plugin.wecom_task.model.model_wecom_task import WecomTask

        # 创建同步数据库连接
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # 查询到期任务
            stmt = select(WecomTask).where(
                and_(
                    WecomTask.status == 1,
                    WecomTask.next_run_time <= current_time
                )
            )
            due_tasks = session.execute(stmt).scalars().all()
            logger.info(f"找到 {len(due_tasks)} 个到期企业微信任务")

            # 处理每个到期任务
            for task in due_tasks:
                try:
                    # 发送消息
                    webhook = WechatWorkWebhook(task.webhook_url)

                    if task.message_type == "text":
                        result = webhook.text(task.message_content)
                    elif task.message_type == "markdown":
                        result = webhook.markdown(task.message_content)
                    else:
                        # 默认使用文本类型
                        logger.warning(f"未知的消息类型 {task.message_type}，使用默认文本类型")
                        result = webhook.text(task.message_content)

                    if result.get("errcode") == 0:
                        logger.info(f"企业微信消息发送成功: {task.name} (ID: {task.id})")
                    else:
                        error_msg = result.get("errmsg", "未知错误")
                        logger.error(f"企业微信消息发送失败: {task.name} (ID: {task.id}), 错误: {error_msg}")

                    # 计算下次运行时间
                    next_run_time = calculate_next_run_time(task.cron_expression)
                    if next_run_time:
                        # 更新下次运行时间
                        task.next_run_time = next_run_time
                        session.commit()
                        logger.info(f"更新企业微信任务下次运行时间: {task.name} (ID: {task.id}) -> {next_run_time}")
                    else:
                        logger.warning(f"无法计算任务下次运行时间: {task.name} (ID: {task.id}), cron表达式: {task.cron_expression}")
                except Exception as e:
                    logger.error(f"执行企业微信任务失败: {task.name} (ID: {task.id}) - {str(e)}")

        return {"success": True, "message": f"检查到期企业微信任务完成，执行了 {len(due_tasks)} 个任务"}
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

    try:
        # 使用SQLAlchemy会话查询数据库
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker
        from backend.core.conf import settings
        from backend.plugin.wecom_task.model.model_wecom_task import WecomTask

        # 创建同步数据库连接
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            # 获取任务
            stmt = select(WecomTask).where(WecomTask.id == task_id)
            task = session.execute(stmt).scalar_one_or_none()

            if not task:
                logger.error(f"未找到ID为 {task_id} 的任务")
                return {"success": False, "message": f"未找到ID为 {task_id} 的任务"}

            # 检查任务状态
            if task.status != 1:
                logger.warning(f"任务 {task.name} (ID: {task.id}) 状态为 {task.status}，跳过执行")
                return {"success": False, "message": f"任务状态为 {task.status}，跳过执行"}

            # 发送消息
            webhook = WechatWorkWebhook(task.webhook_url)
            logger.info(f"发送企业微信消息: {task.name} (ID: {task.id}), 类型: {task.message_type}")

            if task.message_type == "text":
                result = webhook.text(task.message_content)
            elif task.message_type == "markdown":
                result = webhook.markdown(task.message_content)
            elif task.message_type == "image":
                if not task.file_path:
                    logger.error(f"任务 {task.name} (ID: {task.id}) 类型为image，但file_path为空")
                    return {"success": False, "message": "Image message type requires a file_path."}
                try:
                    result = webhook.image(task.file_path)
                except FileNotFoundError:
                    logger.error(f"任务 {task.name} (ID: {task.id}) image file not found: {task.file_path}")
                    return {"success": False, "message": f"Image file not found: {task.file_path}"}
                except Exception as e:
                    logger.error(f"任务 {task.name} (ID: {task.id}) failed to send image: {str(e)}")
                    return {"success": False, "message": f"Failed to send image: {str(e)}"}
            elif task.message_type == "file":
                if not task.file_path:
                    logger.error(f"任务 {task.name} (ID: {task.id}) 类型为file，但file_path为空")
                    return {"success": False, "message": "File message type requires a file_path."}
                try:
                    result = webhook.file(task.file_path)
                except FileNotFoundError:
                    logger.error(f"任务 {task.name} (ID: {task.id}) file not found: {task.file_path}")
                    return {"success": False, "message": f"File not found: {task.file_path}"}
                except Exception as e:
                    logger.error(f"任务 {task.name} (ID: {task.id}) failed to send file: {str(e)}")
                    return {"success": False, "message": f"Failed to send file: {str(e)}"}
            else:
                # 默认使用文本类型
                logger.warning(f"未知的消息类型 {task.message_type}，使用默认文本类型")
                result = webhook.text(task.message_content)

            if result.get("errcode") == 0:
                logger.info(f"企业微信消息发送成功: {task.name} (ID: {task.id})")

                # 计算下次运行时间
                next_run_time = calculate_next_run_time(task.cron_expression)
                if next_run_time:
                    # 更新下次运行时间
                    task.next_run_time = next_run_time
                    session.commit()
                    logger.info(f"更新企业微信任务下次运行时间: {task.name} (ID: {task.id}) -> {next_run_time}")

                return {
                    "success": True,
                    "message": "企业微信消息发送成功",
                    "data": result
                }
            else:
                error_msg = result.get("errmsg", "未知错误")
                logger.error(f"企业微信消息发送失败: {task.name} (ID: {task.id}), 错误: {error_msg}")
                return {
                    "success": False,
                    "message": f"企业微信消息发送失败: {error_msg}",
                    "data": result
                }
    except Exception as e:
        logger.error(f"执行任务失败: {str(e)}")
        return {"success": False, "message": f"执行任务失败: {str(e)}"}
