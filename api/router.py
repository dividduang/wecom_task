#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.core.conf import settings
from backend.plugin.wecom_task.api.v1.wecom import router as wecom_router

v1 = APIRouter(prefix=f'{settings.FASTAPI_API_V1_PATH}/wecom_task')

v1.include_router(wecom_router, tags=['企微定时任务'])

