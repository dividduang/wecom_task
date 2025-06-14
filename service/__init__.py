#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

# 检测当前运行环境
if os.path.basename(os.getcwd()) == 'backend':
    # 在 backend 目录下运行
    sys.path.insert(0, os.getcwd())  # 添加当前工作目录（backend）到 Python 路径

# 导入任务，以便 Celery 能够发现它们
from .tasks import check_due_tasks, execute_wecom_task

__all__ = ['check_due_tasks', 'execute_wecom_task']
    