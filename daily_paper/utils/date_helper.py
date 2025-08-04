"""
Date Helper Utilities

日期处理相关工具函数
"""

import datetime
from typing import Optional


def get_yesterday_date() -> datetime.date:
    """获取昨天的日期"""
    return datetime.date.today() - datetime.timedelta(days=1)


def get_date_by_offset(offset_days: int) -> datetime.date:
    """
    获取相对于今天偏移指定天数的日期
    
    Args:
        offset_days: 偏移天数，负数表示过去，正数表示未来
        
    Returns:
        偏移后的日期
    """
    return datetime.date.today() + datetime.timedelta(days=offset_days)


def parse_date_string(date_str: str) -> datetime.date:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串，支持格式：YYYY-MM-DD
        
    Returns:
        解析后的日期对象
        
    Raises:
        ValueError: 日期格式不正确
    """
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"日期格式不正确，请使用 YYYY-MM-DD 格式：{date_str}")


def format_date_chinese(date: datetime.date) -> str:
    """
    格式化日期为中文显示
    
    Args:
        date: 日期对象
        
    Returns:
        中文格式的日期字符串，如：2025年1月15日
    """
    return f"{date.year}年{date.month}月{date.day}日"


def get_date_range_str(start_date: datetime.date, end_date: datetime.date) -> str:
    """
    获取日期范围字符串
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        日期范围字符串
    """
    if start_date == end_date:
        return format_date_chinese(start_date)
    else:
        return f"{format_date_chinese(start_date)} 至 {format_date_chinese(end_date)}"


if __name__ == "__main__":
    # 测试日期工具函数
    today = datetime.date.today()
    yesterday = get_yesterday_date()
    
    print(f"今天: {format_date_chinese(today)}")
    print(f"昨天: {format_date_chinese(yesterday)}")
    
    # 测试日期解析
    try:
        test_date = parse_date_string("2025-01-15")
        print(f"解析日期: {format_date_chinese(test_date)}")
    except ValueError as e:
        print(f"日期解析错误: {e}")
    
    # 测试日期范围
    range_str = get_date_range_str(yesterday, today)
    print(f"日期范围: {range_str}")