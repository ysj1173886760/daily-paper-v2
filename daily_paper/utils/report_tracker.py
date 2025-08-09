"""
Report Tracking Utilities

管理日报推送状态和日期跟踪
"""

import json
import datetime
from pathlib import Path
from typing import Optional
from daily_paper.utils.logger import logger


class ReportTracker:
    """日报推送状态跟踪器"""
    
    def __init__(self, tracker_file: str = "data/report_tracker.json"):
        """
        初始化跟踪器
        
        Args:
            tracker_file: 跟踪文件路径
        """
        self.tracker_file = Path(tracker_file)
        self.data = self._load_data()
    
    def _load_data(self) -> dict:
        """加载跟踪数据"""
        # 确保目录存在
        self.tracker_file.parent.mkdir(exist_ok=True)
        
        if not self.tracker_file.exists():
            logger.info(f"跟踪文件不存在: {self.tracker_file}, 创建默认数据")
            default_data = {
                "last_pushed_date": None,  # 最后推送的日期
                "push_history": {},        # 推送历史记录 {date: status}
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            self._save_data(default_data)
            return default_data
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"从{self.tracker_file}加载跟踪数据")
                return data
        except Exception as e:
            logger.error(f"加载跟踪文件失败: {e}")
            raise
    
    def _save_data(self, data: dict) -> None:
        """保存跟踪数据"""
        data["updated_at"] = datetime.datetime.now().isoformat()
        try:
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                logger.debug(f"跟踪数据已保存到 {self.tracker_file}")
        except Exception as e:
            logger.error(f"保存跟踪文件失败: {e}")
            raise
    
    def get_last_pushed_date(self) -> Optional[datetime.date]:
        """获取最后推送的日期"""
        last_date_str = self.data.get("last_pushed_date")
        if last_date_str is None:
            return None
        
        if isinstance(last_date_str, str):
            return datetime.datetime.fromisoformat(last_date_str).date()
        elif isinstance(last_date_str, datetime.date):
            return last_date_str
        else:
            logger.warning(f"无法解析的日期格式: {last_date_str}")
            return None
    
    def update_last_pushed_date(self, date: datetime.date) -> None:
        """更新最后推送的日期"""
        self.data["last_pushed_date"] = date.isoformat()
        self._save_data(self.data)
        logger.info(f"更新最后推送日期为: {date}")
    
    def mark_date_pushed(self, date: datetime.date, success: bool = True, details: dict = None) -> None:
        """标记某日期已推送"""
        date_str = date.isoformat()
        push_record = {
            "success": success,
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details or {}
        }
        
        if "push_history" not in self.data:
            self.data["push_history"] = {}
        
        self.data["push_history"][date_str] = push_record
        
        # 如果推送成功，更新最后推送日期
        if success:
            current_last = self.get_last_pushed_date()
            if current_last is None or date > current_last:
                self.update_last_pushed_date(date)
        
        self._save_data(self.data)
        logger.info(f"标记 {date} 推送状态: {'成功' if success else '失败'}")
    
    def is_date_pushed(self, date: datetime.date) -> bool:
        """检查某日期是否已成功推送"""
        date_str = date.isoformat()
        push_history = self.data.get("push_history", {})
        record = push_history.get(date_str)
        
        if record is None:
            return False
        
        return record.get("success", False)
    
    def get_unpushed_dates(self, start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
        """获取指定日期范围内未推送的日期列表"""
        unpushed_dates = []
        current_date = start_date
        
        while current_date <= end_date:
            if not self.is_date_pushed(current_date):
                unpushed_dates.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        return unpushed_dates
    
    def get_next_pending_date(self, until_date: datetime.date = None, skip_no_paper_dates: bool = True) -> Optional[datetime.date]:
        """
        获取下一个待推送的日期
        
        Args:
            until_date: 截止日期，默认为昨天
            skip_no_paper_dates: 是否跳过无论文的日期
        """
        if until_date is None:
            until_date = datetime.date.today() - datetime.timedelta(days=1)  # 默认到昨天
        
        # 确定开始日期
        start_date = self._get_start_date(until_date)
        if start_date is None or start_date > until_date:
            return None  # 没有待推送的日期
        
        # 从开始日期逐日检查
        current_date = start_date
        while current_date <= until_date:
            date_str = current_date.isoformat()
            push_history = self.data.get("push_history", {})
            record = push_history.get(date_str)
            
            if record is None:
                # 未处理过的日期
                return current_date
            elif not record.get("success", False):
                # 处理失败的日期
                details = record.get("details", {})
                reason = details.get("reason", "")
                
                if reason == "no_papers" and skip_no_paper_dates:
                    # 跳过无论文的日期，继续下一天
                    logger.debug(f"跳过无论文日期: {current_date}")
                    current_date += datetime.timedelta(days=1)
                    continue
                else:
                    # 其他失败原因，需要重新处理
                    return current_date
            else:
                # 成功处理的日期，继续下一天
                current_date += datetime.timedelta(days=1)
                continue
        
        return None  # 没有待推送的日期
    
    def _get_start_date(self, until_date: datetime.date) -> Optional[datetime.date]:
        """确定开始检查的日期"""
        # 检查是否有成功的推送记录
        push_history = self.data.get("push_history", {})
        successful_dates = []
        
        for date_str, record in push_history.items():
            if record.get("success", False):
                try:
                    date = datetime.datetime.fromisoformat(date_str).date()
                    successful_dates.append(date)
                except ValueError:
                    continue
        
        if successful_dates:
            # 从最后成功推送的日期的下一天开始
            last_success = max(successful_dates)
            return last_success + datetime.timedelta(days=1)
        else:
            # 没有成功的推送记录，从配置的天数前开始（默认7天前）
            return until_date - datetime.timedelta(days=6)
    
    def get_push_statistics(self) -> dict:
        """获取推送统计信息"""
        push_history = self.data.get("push_history", {})
        total_attempts = len(push_history)
        successful_pushes = sum(1 for record in push_history.values() if record.get("success", False))
        failed_pushes = total_attempts - successful_pushes
        
        return {
            "total_attempts": total_attempts,
            "successful_pushes": successful_pushes,
            "failed_pushes": failed_pushes,
            "success_rate": successful_pushes / total_attempts if total_attempts > 0 else 0,
            "last_pushed_date": self.get_last_pushed_date(),
            "first_attempt_date": min(push_history.keys()) if push_history else None,
            "latest_attempt_date": max(push_history.keys()) if push_history else None
        }


if __name__ == "__main__":
    # 测试ReportTracker
    tracker = ReportTracker("data/test_report_tracker.json")
    
    # 测试基本功能
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    print(f"最后推送日期: {tracker.get_last_pushed_date()}")
    print(f"昨天是否已推送: {tracker.is_date_pushed(yesterday)}")
    
    # 标记昨天已推送
    tracker.mark_date_pushed(yesterday, success=True, details={"papers_count": 5})
    print(f"标记后昨天是否已推送: {tracker.is_date_pushed(yesterday)}")
    
    # 获取下一个待推送日期
    next_date = tracker.get_next_pending_date()
    print(f"下一个待推送日期: {next_date}")
    
    # 获取统计信息
    stats = tracker.get_push_statistics()
    print(f"推送统计: {stats}")
    
    # 清理测试文件
    import os
    test_file = "data/test_report_tracker.json"
    if os.path.exists(test_file):
        os.remove(test_file)
        print("清理测试文件完成")