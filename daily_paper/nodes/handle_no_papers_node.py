"""
Handle No Papers Node

处理没有论文情况的节点
"""

from pocketflow import Node
from daily_paper.utils.logger import logger
from daily_paper.utils.date_helper import format_date_chinese


class HandleNoPapersNode(Node):
    """处理没有论文情况的节点"""
    
    def __init__(self):
        """初始化节点"""
        super().__init__()
    
    def prep(self, shared):
        """准备阶段：获取目标日期和跟踪器"""
        target_date = shared.get("target_date")
        report_tracker = shared.get("report_tracker")
        
        if target_date is None:
            raise ValueError("target_date not found in shared store")
        
        if report_tracker is None:
            raise ValueError("report_tracker not found in shared store")
        
        return {
            "target_date": target_date,
            "report_tracker": report_tracker
        }
    
    def exec(self, prep_res):
        """执行阶段：标记该日期为无论文状态"""
        target_date = prep_res["target_date"]
        tracker = prep_res["report_tracker"]
        
        logger.warning(f"{format_date_chinese(target_date)} 没有找到有效论文，标记为无论文状态")
        
        # 标记为失败，但添加特殊标记表示是因为没有论文
        details = {
            "reason": "no_papers",
            "message": f"{format_date_chinese(target_date)} 没有找到有效论文",
            "skip_retry": True  # 标记不需要重试
        }
        
        tracker.mark_date_pushed(target_date, success=False, details=details)
        
        return {
            "date": target_date,
            "reason": "no_papers",
            "marked": True
        }
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：存储处理结果"""
        shared["no_papers_result"] = exec_res
        
        logger.info(f"已标记 {exec_res['date']} 为无论文状态")
        
        return "default"