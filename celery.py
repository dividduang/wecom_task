#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import celery
import celery_aio_pool
import logging
from celery.schedules import crontab
from functools import lru_cache

from backend.core.conf import settings
from backend.plugin.wecom_task.conf import task_settings

__all__ = ['get_celery_app']

logger = logging.getLogger(__name__)


def init_celery() -> celery.Celery:
    """初始化企业微信插件的 celery 应用"""

    # TODO: Update this work if celery version >= 6.0.0
    # https://github.com/fastapi-practices/fastapi_best_architecture/issues/321
    # https://github.com/celery/celery/issues/7874
    celery.app.trace.build_tracer = celery_aio_pool.build_async_tracer
    celery.app.trace.reset_worker_optimizations()

    # Celery Schedule Tasks
    # https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
    beat_schedule = {
        # 每分钟检查一次企业微信任务
        'check_due_wecom_tasks': {
            'task': 'wecom_check_due_tasks',
            'schedule': crontab(minute='*'),  # 每分钟执行一次
        }
    }

    logger.info("已添加企业微信任务检查定时任务到Celery调度器")

    # Celery Config
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html
    broker_url = (
        f'redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:'
        f'{settings.REDIS_PORT}/{task_settings.CELERY_BROKER_REDIS_DATABASE}'
    )
    result_backend = (
        f'redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:'
        f'{settings.REDIS_PORT}/{task_settings.CELERY_BACKEND_REDIS_DATABASE}'
    )
    result_backend_transport_options = {
        'global_keyprefix': f'{task_settings.CELERY_BACKEND_REDIS_PREFIX}',
        'retry_policy': {
            'timeout': task_settings.CELERY_BACKEND_REDIS_TIMEOUT,
        },
    }

    # 创建独立的Celery实例
    app = celery.Celery(
        'wecom_task_celery',  # 独立的应用名称
        enable_utc=False,
        timezone=settings.DATETIME_TIMEZONE,
        beat_schedule=beat_schedule,
        broker_url=broker_url,
        broker_connection_retry_on_startup=True,
        result_backend=result_backend,
        result_backend_transport_options=result_backend_transport_options,
        task_track_started=True,
        # TODO: Update this work if celery version >= 6.0.0
        worker_pool=celery_aio_pool.pool.AsyncIOPool,
    )

    # 只加载企业微信插件的任务模块
    app.autodiscover_tasks(['plugin.wecom_task.service'])

    logger.info("企业微信插件Celery实例初始化完成")
    return app


@lru_cache()
def get_celery_app() -> celery.Celery:
    return init_celery()
