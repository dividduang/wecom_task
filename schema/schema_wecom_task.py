#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class WecomTaskBase(BaseModel):
    """企业微信任务基础模型"""
    name: str = Field(..., description="任务名称")
    webhook_url: HttpUrl = Field(..., description="企业微信群机器人Webhook地址")
    message_type: str = Field(default="text", description="消息类型(text, markdown, image等)")
    message_content: str = Field(..., description="消息内容")


class WecomTaskCreate(WecomTaskBase):
    """创建企业微信任务模型"""
    schedule_time: str = Field(..., description="定时时间，格式为cron表达式或者自然语言(如：每天9点)")


class WecomTaskUpdate(BaseModel):
    """更新企业微信任务模型"""
    name: Optional[str] = Field(None, description="任务名称")
    webhook_url: Optional[HttpUrl] = Field(None, description="企业微信群机器人Webhook地址")
    message_type: Optional[str] = Field(None, description="消息类型(text, markdown, image等)")
    message_content: Optional[str] = Field(None, description="消息内容")
    schedule_time: Optional[str] = Field(None, description="定时时间，格式为cron表达式或者自然语言(如：每天9点)")
    status: Optional[int] = Field(None, description="状态(0停用 1正常)")


class WecomTaskDetail(WecomTaskBase):
    """企业微信任务详情模型"""
    id: int
    uuid: str
    cron_expression: str
    next_run_time: Optional[datetime] = None
    status: int
    created_time: datetime
    updated_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WecomTaskList(BaseModel):
    """企业微信任务列表模型"""
    tasks: List[WecomTaskDetail]


class WecomTaskResponse(BaseModel):
    """企业微信任务响应模型"""
    id: int
    name: str
    message: str = "任务创建成功"


class WecomTaskTest(BaseModel):
    """测试发送企业微信消息模型"""
    webhook_url: HttpUrl = Field(..., description="企业微信群机器人Webhook地址")
    message_type: str = Field(default="text", description="消息类型(text, markdown, image等)")
    message_content: str = Field(..., description="消息内容")
