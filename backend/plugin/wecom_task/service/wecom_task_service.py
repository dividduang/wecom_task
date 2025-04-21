#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.wecom_task.crud.crud_wecom_task import wecom_task_dao
from backend.plugin.wecom_task.wecom_func import WechatWorkWebhook
from backend.plugin.wecom_task.service.schedule_utils import parse_schedule_time, calculate_next_run_time


class WecomTaskService:
    @staticmethod
    async def create_task(
        name: str,
        webhook_url: str,
        message_type: str,
        message_content: str,
        schedule_time: str
    ) -> Dict[str, Any]:
        """
        创建企业微信任务

        :param name: 任务名称
        :param webhook_url: Webhook地址
        :param message_type: 消息类型
        :param message_content: 消息内容
        :param schedule_time: 定时时间
        :return: 创建的任务信息
        """
        async with async_db_session() as db:
            try:
                # 解析定时时间为cron表达式
                cron_expression = parse_schedule_time(schedule_time)

                # 计算下次运行时间
                next_run_time = calculate_next_run_time(cron_expression)

                # 创建任务
                task = await wecom_task_dao.create_task(
                    db=db,
                    name=name,
                    webhook_url=str(webhook_url),
                    message_type=message_type,
                    message_content=message_content,
                    cron_expression=cron_expression,
                    next_run_time=next_run_time
                )

                # 注册Celery任务
                await WecomTaskService.register_celery_task(task.id, cron_expression)

                return {
                    "id": task.id,
                    "name": task.name,
                    "message": "任务创建成功"
                }
            except Exception as e:
                await db.rollback()
                raise errors.ServerError(msg=f"创建任务失败: {str(e)}")

    @staticmethod
    async def update_task(task_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新企业微信任务

        :param task_id: 任务ID
        :param update_data: 更新数据
        :return: 更新结果
        """
        async with async_db_session() as db:
            try:
                # 获取任务
                task = await wecom_task_dao.select_model_by_column(db, id=task_id)
                if not task:
                    raise errors.NotFoundError(msg=f"未找到ID为 {task_id} 的任务")

                # 处理定时时间
                if "schedule_time" in update_data and update_data["schedule_time"]:
                    cron_expression = parse_schedule_time(update_data["schedule_time"])
                    next_run_time = calculate_next_run_time(cron_expression)
                    update_data["cron_expression"] = cron_expression
                    update_data["next_run_time"] = next_run_time

                    # 更新Celery任务
                    await WecomTaskService.update_celery_task(task_id, cron_expression)

                # 删除schedule_time字段，因为数据库中没有这个字段
                if "schedule_time" in update_data:
                    del update_data["schedule_time"]

                # 更新任务
                updated_task = await wecom_task_dao.update_task(db, task_id, update_data)
                if not updated_task:
                    raise errors.ServerError(msg="更新任务失败")

                return {
                    "id": updated_task.id,
                    "name": updated_task.name,
                    "message": "任务更新成功"
                }
            except errors.NotFoundError as e:
                await db.rollback()
                raise e
            except Exception as e:
                await db.rollback()
                raise errors.ServerError(msg=f"更新任务失败: {str(e)}")

    @staticmethod
    async def delete_task(task_id: int) -> Dict[str, Any]:
        """
        删除企业微信任务

        :param task_id: 任务ID
        :return: 删除结果
        """
        async with async_db_session() as db:
            try:
                # 获取任务
                task = await wecom_task_dao.select_model_by_column(db, id=task_id)
                if not task:
                    raise errors.NotFoundError(msg=f"未找到ID为 {task_id} 的任务")

                # 删除任务
                await db.delete(task)
                await db.commit()

                # 删除Celery任务
                await WecomTaskService.delete_celery_task(task_id)

                return {
                    "message": "任务删除成功"
                }
            except errors.NotFoundError as e:
                await db.rollback()
                raise e
            except Exception as e:
                await db.rollback()
                raise errors.ServerError(msg=f"删除任务失败: {str(e)}")

    @staticmethod
    async def get_task(task_id: int) -> Dict[str, Any]:
        """
        获取企业微信任务

        :param task_id: 任务ID
        :return: 任务信息
        """
        async with async_db_session() as db:
            try:
                # 获取任务
                task = await wecom_task_dao.select_model_by_column(db, id=task_id)
                if not task:
                    raise errors.NotFoundError(msg=f"未找到ID为 {task_id} 的任务")

                return task
            except errors.NotFoundError as e:
                raise e
            except Exception as e:
                raise errors.ServerError(msg=f"获取任务失败: {str(e)}")

    @staticmethod
    async def get_all_tasks() -> List[Dict[str, Any]]:
        """
        获取所有企业微信任务

        :return: 任务列表
        """
        async with async_db_session() as db:
            try:
                # 获取所有任务
                tasks = await wecom_task_dao.get_all(db)
                return tasks
            except Exception as e:
                raise errors.ServerError(msg=f"获取任务列表失败: {str(e)}")

    @staticmethod
    async def test_send_message(webhook_url: str, message_type: str, message_content: str) -> Dict[str, Any]:
        """
        测试发送企业微信消息

        :param webhook_url: Webhook地址
        :param message_type: 消息类型
        :param message_content: 消息内容
        :return: 发送结果
        """
        try:
            # 使用现有的WechatWorkWebhook类发送消息
            webhook = WechatWorkWebhook(str(webhook_url))

            if message_type == "text":
                result = webhook.text(message_content)
            elif message_type == "markdown":
                result = webhook.markdown(message_content)
            else:
                # 默认使用文本类型
                result = webhook.text(message_content)

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
            raise errors.ServerError(msg=f"发送消息失败: {str(e)}")

    @staticmethod
    async def execute_task(task_id: int) -> Dict[str, Any]:
        """
        执行企业微信任务

        :param task_id: 任务ID
        :return: 执行结果
        """
        async with async_db_session() as db:
            try:
                # 获取任务
                task = await wecom_task_dao.select_model_by_column(db, id=task_id)
                if not task:
                    raise errors.NotFoundError(msg=f"未找到ID为 {task_id} 的任务")

                # 发送消息
                result = await WecomTaskService.test_send_message(
                    webhook_url=task.webhook_url,
                    message_type=task.message_type,
                    message_content=task.message_content
                )

                # 更新下次运行时间
                next_run_time = calculate_next_run_time(task.cron_expression)
                if next_run_time:
                    await wecom_task_dao.update_next_run_time(db, task_id, next_run_time)

                return result
            except errors.NotFoundError as e:
                raise e
            except Exception as e:
                raise errors.ServerError(msg=f"执行任务失败: {str(e)}")

    @staticmethod
    async def register_celery_task(task_id: int, cron_expression: str) -> None:
        """
        注册Celery任务

        :param task_id: 任务ID
        :param cron_expression: Cron表达式
        """
        try:
            # 尝试导入Celery相关模块
            from backend.app.task.celery import celery_app
            from celery.schedules import crontab

            # 解析cron表达式
            cron_parts = cron_expression.split()
            if len(cron_parts) >= 5:
                minute, hour, day_of_month, month_of_year, day_of_week = cron_parts[:5]

                # 处理特殊字符
                day_of_week = day_of_week.replace("?", "*").replace("7", "0")
                day_of_month = day_of_month.replace("?", "*")

                # 确保日期和月份字段不为 0
                if day_of_month == "0":
                    day_of_month = "1"
                if month_of_year == "0":
                    month_of_year = "1"

                # 创建crontab对象
                cron = crontab(
                    minute=minute,
                    hour=hour,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                    day_of_week=day_of_week
                )

                # 注册定时任务
                celery_app.conf.beat_schedule[f'wecom_task_{task_id}'] = {
                    'task': 'wecom_execute_task',
                    'schedule': cron,
                    'args': (task_id,),
                }

                # 重新加载配置
                celery_app.conf.update()
                logging.info(f"注册企业微信任务成功: {task_id}, 计划: {cron_expression}")
        except ImportError:
            # 如果无法导入Celery相关模块，则记录日志
            logging.warning(f"Celery相关模块导入失败，无法注册定时任务 {task_id}")
        except Exception as e:
            logging.error(f"注册Celery任务失败: {str(e)}")

    @staticmethod
    async def update_celery_task(task_id: int, cron_expression: str) -> None:
        """
        更新Celery任务

        :param task_id: 任务ID
        :param cron_expression: Cron表达式
        """
        try:
            # 先删除旧任务
            await WecomTaskService.delete_celery_task(task_id)

            # 注册新任务
            await WecomTaskService.register_celery_task(task_id, cron_expression)
        except Exception as e:
            logging.error(f"更新Celery任务失败: {str(e)}")

    @staticmethod
    async def delete_celery_task(task_id: int) -> None:
        """
        删除Celery任务

        :param task_id: 任务ID
        """
        try:
            # 尝试导入Celery相关模块
            from backend.app.task.celery import celery_app

            # 删除定时任务
            if f'wecom_task_{task_id}' in celery_app.conf.beat_schedule:
                del celery_app.conf.beat_schedule[f'wecom_task_{task_id}']

                # 重新加载配置
                celery_app.conf.update()
                logging.info(f"删除企业微信任务成功: {task_id}")
        except ImportError:
            # 如果无法导入Celery相关模块，则记录日志
            logging.warning(f"Celery相关模块导入失败，无法删除定时任务 {task_id}")
        except Exception as e:
            logging.error(f"删除Celery任务失败: {str(e)}")


# 创建服务实例
wecom_task_service = WecomTaskService()


# 初始化函数
async def initialize_wecom_tasks():
    """
    初始化企业微信任务，从数据库中加载所有任务并注册到Celery中
    """
    try:
        logging.info("正在初始化企业微信任务...")
        async with async_db_session() as db:
            # 获取所有活动状态的任务
            tasks = await wecom_task_dao.get_all_active_tasks(db)
            logging.info(f"从数据库中加载了 {len(tasks)} 个任务")

            # 注册每个任务到Celery中
            for task in tasks:
                await WecomTaskService.register_celery_task(task.id, task.cron_expression)
                logging.info(f"注册任务: {task.name} (ID: {task.id})")

                # 更新下次运行时间
                next_run_time = calculate_next_run_time(task.cron_expression)
                if next_run_time:
                    await wecom_task_dao.update_next_run_time(db, task.id, next_run_time)
                    logging.info(f"更新任务下次运行时间: {task.name} (ID: {task.id}) -> {next_run_time}")

        # 注册定期检查任务
        await register_check_due_tasks()
        logging.info("企业微信任务初始化完成")
    except Exception as e:
        logging.error(f"初始化企业微信任务失败: {str(e)}")


# 注册定期检查任务
async def register_check_due_tasks():
    """
    注册定期检查任务，用于检查是否有到期的任务需要执行
    """
    try:
        # 尝试导入Celery相关模块
        from backend.app.task.celery import celery_app
        from celery.schedules import crontab

        # 每分钟检查一次
        celery_app.conf.beat_schedule['check_due_wecom_tasks'] = {
            'task': 'wecom_check_due_tasks',
            'schedule': crontab(minute='*'),  # 每分钟执行一次
        }

        # 重新加载配置
        celery_app.conf.update()
        logging.info("已注册定期检查企业微信任务")

        # 手动触发一次任务，确保它能正常工作
        try:
            result = celery_app.send_task('wecom_check_due_tasks')
            logging.info(f"手动触发企业微信任务成功，任务ID: {result.id}")
        except Exception as e:
            logging.error(f"手动触发企业微信任务失败: {str(e)}")
    except ImportError:
        logging.warning("Celery相关模块导入失败，无法注册定期检查任务")
    except Exception as e:
        logging.error(f"注册定期检查任务失败: {str(e)}")


# 从 service/tasks.py 中导入Celery任务
try:
    from backend.plugin.wecom_task.service.tasks import execute_wecom_task
except ImportError:
    logging.warning("Celery任务导入失败")

    # 定义一个空函数作为占位符
    def execute_wecom_task(task_id: int):
        logging.error(f"Celery任务模块未加载，无法执行任务 {task_id}")
        return None
