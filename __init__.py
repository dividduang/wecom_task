#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Global flag to prevent repeated initialization
INITIALIZED = False

import asyncio
import logging
import os
import sys
from functools import partial

# 检测当前运行环境
if os.path.basename(os.getcwd()) == 'backend':
    # 在 backend 目录下运行
    sys.path.insert(0, os.getcwd())  # 添加当前工作目录（backend）到 Python 路径

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if not INITIALIZED:
    # 初始化插件
    try:
        # 导入插件配置
        try:
            from core.conf import settings
            from plugin.wecom_task import conf  # noqa
        except ImportError:
            from backend.core.conf import settings
            from backend.plugin.wecom_task import conf  # noqa
        logging.info("企业微信插件配置已加载")

        # 导入插件的Celery实例
        try:
            from plugin.wecom_task.celery import celery_app  # noqa
        except ImportError:
            from backend.plugin.wecom_task.celery import celery_app  # noqa
        logging.info("企业微信插件Celery实例已加载")

        # 导入任务模块，确保任务被注册
        try:
            from plugin.wecom_task.service import tasks  # noqa
        except ImportError:
            from backend.plugin.wecom_task.service import tasks  # noqa
        logging.info("企业微信插件任务已加载")

        # 手动触发一次任务检查，确保它能正常工作
        try:
            result = celery_app.send_task('wecom_check_due_tasks')
            logging.info(f"手动触发企业微信任务成功，任务ID: {result.id}")
        except Exception as e:
            logging.warning(f"手动触发企业微信任务失败: {str(e)}")
    except Exception as e:
        logging.warning(f"加载企业微信插件失败: {str(e)}")


# 异步初始化函数
async def _async_init():
    try:
        # 导入初始化函数
        try:
            from plugin.wecom_task.service.wecom_task_service import initialize_wecom_tasks
        except ImportError:
            from backend.plugin.wecom_task.service.wecom_task_service import initialize_wecom_tasks

        # 执行初始化
        await initialize_wecom_tasks()
        logging.info("企业微信任务数据库初始化完成")
    except Exception as e:
        logging.error(f"初始化企业微信任务失败: {str(e)}")


# 在主线程中运行异步初始化
def init():
    try:
        # 获取或创建事件循环
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 在下一个循环中调用异步初始化函数
        loop.call_soon(partial(asyncio.create_task, _async_init()))
        logging.info("企业微信任务初始化已调度")
    except Exception as e:
        logging.error(f"调度企业微信任务初始化失败: {str(e)}")


# 在插件加载时执行初始化
if not INITIALIZED:
    try:
        # 执行数据库初始化
        init()
        logging.info("企业微信插件初始化完成")
    except Exception as e:
        logging.error(f"企业微信插件初始化失败: {str(e)}")

    INITIALIZED = True
