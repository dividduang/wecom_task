#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, HTTPException
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
    # Validation based on message_type
    if task.message_type in ["image", "file"]:
        if not task.file_path:
            raise HTTPException(status_code=422, detail="File path is required for image/file message types.")
        # Optionally clear message_content if file_path is present
        # task.message_content = None 
    elif task.message_type in ["text", "markdown"]:
        if not task.message_content:
            raise HTTPException(status_code=422, detail="Message content is required for text/markdown message types.")
        # Optionally clear file_path if message_content is present
        # task.file_path = None
    else:
        # Handle unknown message_type if necessary, or let Pydantic validation catch it if it's an enum
        pass

    result = await wecom_task_service.create_task(
        name=task.name,
        webhook_url=str(task.webhook_url),
        message_type=task.message_type,
        message_content=task.message_content,
        schedule_time=task.schedule_time,
        file_path=task.file_path  # Ensure service method accepts this
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
    task: WecomTaskUpdate = None,
    db: CurrentSession = Depends() # Added to fetch existing task
) -> ResponseSchemaModel[WecomTaskResponse]:
    """
    更新企业微信任务

    :param task_id: 任务ID
    :param task: 更新的任务信息
    :param db: 数据库会话
    :return: 更新结果
    """
    update_data = task.model_dump(exclude_unset=True) if task else {}

    if update_data: # Only validate if there's something to update
        # Determine the final message_type
        final_message_type = update_data.get("message_type")
        final_file_path = update_data.get("file_path")
        final_message_content = update_data.get("message_content")

        if "message_type" in update_data or "file_path" in update_data or "message_content" in update_data:
            # If message_type, file_path, or message_content is being updated, we need to validate
            # Fetch existing task to get current values if not all are provided in update_data
            existing_task = await wecom_task_service.get_task_model(db, task_id) # Needs this method in service
            if not existing_task:
                raise HTTPException(status_code=404, detail="Task not found")

            current_message_type = existing_task.message_type
            current_file_path = existing_task.file_path
            current_message_content = existing_task.message_content

            # Determine final values for validation
            val_message_type = update_data.get("message_type", current_message_type)
            val_file_path = update_data.get("file_path", current_file_path)
            # If file_path is explicitly set to None in payload, it should be None
            if "file_path" in update_data and update_data["file_path"] is None:
                val_file_path = None
            
            val_message_content = update_data.get("message_content", current_message_content)
            # If message_content is explicitly set to None in payload, it should be None
            if "message_content" in update_data and update_data["message_content"] is None:
                val_message_content = None


            if val_message_type in ["image", "file"]:
                if not val_file_path:
                    raise HTTPException(status_code=422, detail="File path is required for image/file message types.")
                # If type is image/file, and message_content is not being cleared, clear it from update_data
                if "message_content" not in update_data and val_message_content: # content exists from db
                     update_data["message_content"] = None # Set it to None for update
                elif "message_content" in update_data and update_data["message_content"] is not None:
                     update_data["message_content"] = None # Explicitly clear it

            elif val_message_type in ["text", "markdown"]:
                if not val_message_content:
                    raise HTTPException(status_code=422, detail="Message content is required for text/markdown message types.")
                # If type is text/markdown, and file_path is not being cleared, clear it from update_data
                if "file_path" not in update_data and val_file_path: # path exists from db
                    update_data["file_path"] = None # Set it to None for update
                elif "file_path" in update_data and update_data["file_path"] is not None:
                    update_data["file_path"] = None # Explicitly clear it
    
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
    # Validation for test endpoint
    if test.message_type in ["image", "file"]:
        if not test.file_path:
            raise HTTPException(status_code=422, detail="File path is required for image/file message types.")
    elif test.message_type in ["text", "markdown"]:
        if not test.message_content:
            raise HTTPException(status_code=422, detail="Message content is required for text/markdown message types.")
    
    result = await wecom_task_service.test_send_message(
        webhook_url=str(test.webhook_url),
        message_type=test.message_type,
        message_content=test.message_content,
        file_path=test.file_path # Ensure service method accepts this
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
