"""
Update Push Status Node

更新推送状态的节点
"""

import datetime
from typing import Dict, Any
from pocketflow import Node
from daily_paper.utils.logger import logger
from daily_paper.utils.report_tracker import ReportTracker
from daily_paper.utils.date_helper import format_date_chinese


class UpdatePushStatusNode(Node):
    """更新推送状态的节点"""
    
    def __init__(self):
        """初始化节点"""
        super().__init__()
    
    def prep(self, shared):
        """准备阶段：从shared获取推送结果和目标日期"""
        push_result = shared.get("push_result")
        target_date = shared.get("target_date")
        report_tracker = shared.get("report_tracker")
        
        if push_result is None:
            raise ValueError("push_result not found in shared store")
        
        if target_date is None:
            raise ValueError("target_date not found in shared store")
        
        if report_tracker is None:
            raise ValueError("report_tracker not found in shared store")
        
        return {
            "push_result": push_result,
            "target_date": target_date,
            "report_tracker": report_tracker
        }
    
    def exec(self, prep_res):
        """执行阶段：更新推送状态"""
        push_result = prep_res["push_result"]
        target_date = prep_res["target_date"]
        tracker = prep_res["report_tracker"]
        
        success = push_result.get("success", False)
        
        # 构建详细信息
        details = {
            "push_method": "feishu",
            "fallback_used": push_result.get("fallback", False)
        }
        
        if success:
            details.update({
                "content_length": len(push_result.get("content", "")),
                "feishu_result": push_result.get("result", {})
            })
        else:
            details.update({
                "error": push_result.get("error", "Unknown error")
            })
        
        # 更新推送状态
        tracker.mark_date_pushed(target_date, success=success, details=details)
        
        logger.info(f"已更新 {format_date_chinese(target_date)} 的推送状态: "
                   f"{'成功' if success else '失败'}")
        
        return {
            "success": success,
            "date": target_date,
            "details": details
        }
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：存储更新结果"""
        shared["status_update_result"] = exec_res
        
        if exec_res["success"]:
            logger.info(f"推送状态更新成功: {exec_res['date']}")
        else:
            logger.warning(f"推送失败已记录: {exec_res['date']}")
        
        return "default"