#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from pydantic import HttpUrl

from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession
from backend.plugin.wecom_task.schema.schema_wecom_task import (
    WecomTaskCreate,
    WecomTaskUpdate,
    WecomTaskResponse,
    WecomTaskDetail,
    WecomTaskTest
)
from backend.plugin.wecom_task.service.wecom_task_service import wecom_task_service

router = APIRouter()


@router.post(
    '',
    summary='创建企业微信任务',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def create_wecom_task(task: WecomTaskCreate) -> ResponseSchemaModel[WecomTaskResponse]:
    """
    创建企业微信任务

    :param task: 任务信息
    :return: 创建结果
    """
    result = await wecom_task_service.create_task(
        name=task.name,
        webhook_url=str(task.webhook_url),
        message_type=task.message_type,
        message_content=task.message_content,
        schedule_time=task.schedule_time
    )
    return response_base.success(data=WecomTaskResponse(**result))


@router.put(
    '/{task_id}',
    summary='更新企业微信任务',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def update_wecom_task(
    task_id: int = Path(..., description='任务ID'),
    task: WecomTaskUpdate = None
) -> ResponseSchemaModel[WecomTaskResponse]:
    """
    更新企业微信任务

    :param task_id: 任务ID
    :param task: 更新的任务信息
    :return: 更新结果
    """
    update_data = task.model_dump(exclude_unset=True) if task else {}
    result = await wecom_task_service.update_task(task_id, update_data)
    return response_base.success(data=WecomTaskResponse(**result))


@router.delete(
    '/{task_id}',
    summary='删除企业微信任务',
    dependencies=[
        DependsJwtAuth,
    ],
)
async def delete_wecom_task(task_id: int = Path(..., description='任务ID')) -> ResponseModel:
    """
    删除企业微信任务

    :param task_id: 任务ID
    :return: 删除结果
    """
    await wecom_task_service.delete_task(task_id)
    return response_base.success(msg="删除成功")


@router.get(
    '/{task_id}',
    summary='获取企业微信任务详情',
    dependencies=[DependsJwtAuth],
)
async def get_wecom_task(task_id: int = Path(..., description='任务ID')) -> ResponseSchemaModel[WecomTaskDetail]:
    """
    获取企业微信任务详情

    :param task_id: 任务ID
    :return: 任务详情
    """
    task = await wecom_task_service.get_task(task_id)
    return response_base.success(data=task)


@router.get(
    '',
    summary='获取企业微信任务列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_wecom_tasks(
    db: CurrentSession,
    name: Optional[str] = Query(None, description='任务名称'),
    status: Optional[int] = Query(None, description='状态(0停用 1正常)'),
) -> ResponseSchemaModel[PageData[WecomTaskDetail]]:
    """
    获取企业微信任务列表

    :param db: 数据库会话
    :param name: 任务名称
    :param status: 状态
    :return: 任务列表
    """
    from sqlalchemy import select
    from backend.plugin.wecom_task.model.model_wecom_task import WecomTask
    
    # 构建查询
    query = select(WecomTask)
    if name:
        query = query.filter(WecomTask.name.like(f"%{name}%"))
    if status is not None:
        query = query.filter(WecomTask.status == status)
    
    # 分页查询
    page_data = await paging_data(db, query)
    return response_base.success(data=page_data)


@router.post(
    '/test',
    summary='测试发送企业微信消息',
    dependencies=[DependsJwtAuth],
)
async def test_wecom_message(test: WecomTaskTest) -> ResponseModel:
    """
    测试发送企业微信消息

    :param test: 测试信息
    :return: 发送结果
    """
    result = await wecom_task_service.test_send_message(
        webhook_url=str(test.webhook_url),
        message_type=test.message_type,
        message_content=test.message_content
    )
    
    if result.get("success"):
        return response_base.success(msg="发送成功")
    else:
        return response_base.fail(msg=result.get("message", "发送失败"))


@router.post(
    '/execute/{task_id}',
    summary='立即执行企业微信任务',
    dependencies=[DependsJwtAuth],
)
async def execute_wecom_task(task_id: int = Path(..., description='任务ID')) -> ResponseModel:
    """
    立即执行企业微信任务

    :param task_id: 任务ID
    :return: 执行结果
    """
    result = await wecom_task_service.execute_task(task_id)
    
    if result.get("success"):
        return response_base.success(msg="执行成功")
    else:
        return response_base.fail(msg=result.get("message", "执行失败"))
