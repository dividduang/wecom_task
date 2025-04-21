#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import Optional

from croniter import croniter

logger = logging.getLogger(__name__)


def parse_schedule_time(schedule_time: str) -> str:
    """
    解析定时时间，将自然语言转换为cron表达式

    :param schedule_time: 定时时间，格式为cron表达式或者自然语言
    :return: cron表达式
    """
    # 如果已经是cron表达式，直接返回
    parts = schedule_time.split()
    if len(parts) == 5 or len(parts) == 6:
        try:
            # 如果是6位的cron表达式（包含秒字段），去掉秒字段
            if len(parts) == 6:
                schedule_time = ' '.join(parts[1:])  # 去掉秒字段

            # 验证cron表达式是否有效
            croniter(schedule_time, datetime.now())

            # 确保日期和月份字段不为 0
            parts = schedule_time.split()
            if len(parts) >= 5:
                minute, hour, day_of_month, month_of_year, day_of_week = parts[:5]

                if day_of_month == "0":
                    day_of_month = "1"
                if month_of_year == "0":
                    month_of_year = "1"

                return f"{minute} {hour} {day_of_month} {month_of_year} {day_of_week}"

            return schedule_time
        except ValueError as e:
            logger.warning(f"无效的cron表达式: {schedule_time}, 错误: {str(e)}")
            pass

    # 自然语言转换为cron表达式
    schedule_time = schedule_time.lower()

    # 每天特定时间
    if "每天" in schedule_time:
        time_parts = schedule_time.split("每天")[1].strip()
        if "点" in time_parts:
            hour = time_parts.split("点")[0].strip()
            minute = "0"
            if ":" in hour:
                hour, minute = hour.split(":")
            elif "：" in hour:
                hour, minute = hour.split("：")
            try:
                hour = int(hour)
                minute = int(minute)
                return f"0 {minute} {hour} * * ?"
            except ValueError:
                pass

    # 每周特定时间
    if "每周" in schedule_time or "每星期" in schedule_time:
        week_map = {
            "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "日": "0", "天": "0",
            "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "0", "0": "0"
        }
        for day, value in week_map.items():
            if f"每周{day}" in schedule_time or f"每星期{day}" in schedule_time:
                time_parts = schedule_time.split(f"每周{day}")[-1].strip() if f"每周{day}" in schedule_time else schedule_time.split(f"每星期{day}")[-1].strip()
                if "点" in time_parts:
                    hour = time_parts.split("点")[0].strip()
                    minute = "0"
                    if ":" in hour:
                        hour, minute = hour.split(":")
                    elif "：" in hour:
                        hour, minute = hour.split("：")
                    try:
                        hour = int(hour)
                        minute = int(minute)
                        return f"0 {minute} {hour} ? * {value}"
                    except ValueError:
                        pass

    # 每月特定日期
    if "每月" in schedule_time:
        day_parts = schedule_time.split("每月")[1].strip()
        if "号" in day_parts:
            day = day_parts.split("号")[0].strip()
            time_parts = day_parts.split("号")[1].strip()
            hour = "0"
            minute = "0"
            if "点" in time_parts:
                hour = time_parts.split("点")[0].strip()
                if ":" in hour:
                    hour, minute = hour.split(":")
                elif "：" in hour:
                    hour, minute = hour.split("：")
            try:
                day = int(day)
                hour = int(hour)
                minute = int(minute)
                return f"0 {minute} {hour} {day} * ?"
            except ValueError:
                pass

    # 默认返回每天0点的cron表达式
    return "0 0 0 * * ?"


def calculate_next_run_time(cron_expression: str) -> Optional[datetime]:
    """
    计算下次运行时间

    :param cron_expression: cron表达式
    :return: 下次运行时间
    """
    try:
        # 处理cron表达式中的问号，将其替换为*
        cron_expression = cron_expression.replace("?", "*")

        # 创建croniter对象
        cron = croniter(cron_expression, datetime.now())

        # 获取下次运行时间
        next_run_time = cron.get_next(datetime)
        return next_run_time
    except Exception as e:
        logger.exception(f"计算下次运行时间异常: {str(e)}")
        return None
