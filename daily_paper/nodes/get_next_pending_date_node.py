"""
Get Next Pending Date Node

获取下一个待推送日报日期的节点
"""

import datetime
from typing import Optional
from pocketflow import Node
from daily_paper.utils.logger import logger
from daily_paper.utils.report_tracker import ReportTracker
from daily_paper.utils.date_helper import format_date_chinese


class GetNextPendingDateNode(Node):
    """获取下一个待推送日报日期的节点"""
    
    def __init__(self, tracker_file: str = "data/report_tracker.json"):
        """
        初始化节点
        
        Args:
            tracker_file: 跟踪文件路径
        """
        super().__init__()
        self.tracker_file = tracker_file
    
    def prep(self, shared):
        """准备阶段：初始化报告跟踪器"""
        config = shared.get("config")
        # 从配置中获取是否跳过无论文日期的设置
        skip_no_paper_dates = True  # 默认跳过
        if config and hasattr(config, 'daily_summary_skip_no_paper_dates'):
            skip_no_paper_dates = config.daily_summary_skip_no_paper_dates
        
        return {
            "tracker_file": self.tracker_file,
            "skip_no_paper_dates": skip_no_paper_dates
        }
    
    def exec(self, prep_res):
        """执行阶段：获取下一个待推送的日期"""
        tracker = ReportTracker(prep_res["tracker_file"])
        
        # 获取统计信息
        stats = tracker.get_push_statistics()
        logger.info(f"当前推送统计: 总尝试{stats['total_attempts']}次, "
                   f"成功{stats['successful_pushes']}次, "
                   f"最后推送日期: {stats['last_pushed_date']}")
        
        # 获取下一个待推送日期（默认到昨天）
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        skip_no_paper_dates = prep_res["skip_no_paper_dates"]
        next_date = tracker.get_next_pending_date(until_date=yesterday, skip_no_paper_dates=skip_no_paper_dates)
        
        if next_date is None:
            logger.info("没有待推送的日期，所有日报都已推送完毕")
            return {
                "has_pending": False,
                "next_date": None,
                "message": "所有日报都已推送完毕"
            }
        
        logger.info(f"下一个待推送的日期: {format_date_chinese(next_date)}")
        
        return {
            "has_pending": True,
            "next_date": next_date,
            "message": f"准备处理 {format_date_chinese(next_date)} 的日报"
        }
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：将结果存储到shared并决定下一步行动"""
        shared["next_pending_result"] = exec_res
        
        # 将跟踪器也存储到shared，供后续节点使用
        shared["report_tracker"] = ReportTracker(prep_res["tracker_file"])
        
        if exec_res["has_pending"]:
            shared["target_date"] = exec_res["next_date"]
            logger.info(f"设置目标日期为: {exec_res['next_date']}")
            return "has_pending"  # 继续处理
        else:
            logger.info("没有待处理的日期")
            return "no_pending"  # 结束流程