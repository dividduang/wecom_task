#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.path_conf import BASE_PATH


class TaskSettings(BaseSettings):
    """WecomTask Plugin Settings"""

    model_config = SettingsConfigDict(env_file=f'{BASE_PATH}/.env', env_file_encoding='utf-8', extra='ignore')

    # Env Celery - 使用与主应用相同的环境变量
    CELERY_BROKER_REDIS_DATABASE: int
    CELERY_BACKEND_REDIS_DATABASE: int

    # Celery
    CELERY_BROKER: str = 'redis'
    CELERY_BACKEND_REDIS_PREFIX: str = 'wecom:celery:'  # 独立的前缀
    CELERY_BACKEND_REDIS_TIMEOUT: int = 5
    CELERY_TASK_MAX_RETRIES: int = 5

    # 企业微信插件特有配置
    WECOM_TASK_CHECK_INTERVAL: int = 60  # 检查间隔（秒）
    WECOM_TASK_REDIS_PREFIX: str = 'wecom:task:'  # Redis键前缀


@lru_cache
def get_task_settings() -> TaskSettings:
    """获取企业微信插件配置"""
    return TaskSettings()


task_settings = get_task_settings()
