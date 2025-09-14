"""
Batch Daily Report Flow

批量生成日报的工作流
"""

import datetime
from pocketflow import Flow, BatchFlow
from daily_paper.nodes.get_next_pending_date_node import GetNextPendingDateNode
from daily_paper.nodes.fetch_yesterday_papers_node import FetchYesterdayPapersNode
from daily_paper.nodes.analyze_and_recommend_papers_node import AnalyzeAndRecommendPapersNode
from daily_paper.nodes.push_daily_report_to_feishu_node import PushDailyReportToFeishuNode
from daily_paper.nodes.update_push_status_node import UpdatePushStatusNode
from daily_paper.utils.logger import logger
from daily_paper.utils.date_helper import format_date_chinese


class BatchDailyReportFlow(Flow):
    """批量日报生成工作流"""
    
    def __init__(self, max_days: int = 7, tracker_file: str = "data/report_tracker.json"):
        """
        初始化批量日报工作流
        
        Args:
            max_days: 最多处理的天数
            tracker_file: 跟踪文件路径
        """
        self.max_days = max_days
        self.tracker_file = tracker_file
        
        # 创建节点
        self.get_next_date_node = GetNextPendingDateNode(tracker_file=tracker_file)
        self.fetch_papers_node = FetchYesterdayPapersNode()  # 会根据target_date动态调整
        self.analyze_node = AnalyzeAndRecommendPapersNode()
        self.push_node = PushDailyReportToFeishuNode()
        self.update_status_node = UpdatePushStatusNode()
        
        # 设置工作流连接
        self._setup_flow()
        
        # 初始化Flow
        super().__init__(start=self.get_next_date_node)
    
    def _setup_flow(self):
        """设置工作流连接"""
        # 有待处理日期时的正常流程
        self.get_next_date_node - "has_pending" >> self.fetch_papers_node
        self.fetch_papers_node >> self.analyze_node
        self.analyze_node >> self.push_node
        self.push_node >> self.update_status_node
        
        # 更新状态后，检查是否还有待处理的日期（通过重新开始）
        self.update_status_node >> self.get_next_date_node
        
        # 没有待处理日期时结束
        # get_next_date_node 返回 "no_pending" 时自然结束
    
    def prep(self, shared):
        """Flow的准备阶段：初始化shared数据结构"""
        # 确保paper_manager存在
        if "paper_manager" not in shared:
            raise ValueError("paper_manager must be provided in shared store")
        
        # 初始化处理计数器
        shared["processed_days"] = 0
        shared["max_days"] = self.max_days
        
        logger.info(f"开始批量日报处理，最多处理 {self.max_days} 天")
        return None
    
    def post(self, shared, prep_res, exec_res):
        """Flow的后处理阶段：记录处理结果"""
        processed_days = shared.get("processed_days", 0)
        logger.info(f"批量日报处理完成，共处理了 {processed_days} 天")
        
        # 返回处理结果
        return "completed"


class SingleDayReportNode(Flow):
    """单日报告生成节点（作为Flow节点使用）"""
    
    def __init__(self, target_date: datetime.date):
        """
        初始化单日报告节点
        
        Args:
            target_date: 目标日期
        """
        self.target_date = target_date
        
        # 创建节点，传入目标日期
        self.fetch_papers_node = FetchYesterdayPapersNode(target_date=target_date)
        self.analyze_node = AnalyzeAndRecommendPapersNode()
        self.push_node = PushDailyReportToFeishuNode()
        
        # 设置连接
        self.fetch_papers_node >> self.analyze_node >> self.push_node
        
        # 初始化Flow
        super().__init__(start=self.fetch_papers_node)
    
    def prep(self, shared):
        """准备阶段：设置目标日期"""
        shared["target_date"] = self.target_date
        logger.info(f"准备生成 {format_date_chinese(self.target_date)} 的日报")
        return None
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：检查结果"""
        push_result = shared.get("push_result")
        if push_result and push_result.get("success"):
            logger.info(f"{format_date_chinese(self.target_date)} 的日报生成并推送成功")
            return "success"
        else:
            logger.error(f"{format_date_chinese(self.target_date)} 的日报生成或推送失败")
            return "failed"


class BatchDailyReportProcessor:
    """批量日报处理器（主要入口）"""
    
    def __init__(self, max_days: int = 7, tracker_file: str = "data/report_tracker.json"):
        """
        初始化处理器
        
        Args:
            max_days: 最多处理的天数
            tracker_file: 跟踪文件路径
        """
        self.max_days = max_days
        self.tracker_file = tracker_file
    
    def run(self, shared: dict) -> dict:
        """
        运行批量日报处理
        
        Args:
            shared: 共享数据存储
            
        Returns:
            处理结果
        """
        logger.info(f"开始批量日报处理，最多处理 {self.max_days} 天")
        
        # 创建并运行批量工作流
        batch_flow = BatchDailyReportFlow(
            max_days=self.max_days,
            tracker_file=self.tracker_file
        )
        
        try:
            result = batch_flow.run(shared)
            
            processed_days = shared.get("processed_days", 0)
            logger.info(f"批量日报处理完成，共处理 {processed_days} 天")
            
            return {
                "success": True,
                "processed_days": processed_days,
                "max_days": self.max_days,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"批量日报处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_days": shared.get("processed_days", 0)
            }


if __name__ == "__main__":
    # 测试批量日报处理器
    from daily_paper.utils.data_manager import PaperMetaManager
    from daily_paper.utils.call_llm import LLM
    import os
    
    # 创建测试用的shared数据（需要提供 LLM 实例）
    shared = {
        "paper_manager": PaperMetaManager("data/papers.parquet"),
        "llm": LLM(os.getenv("LLM_BASE_URL", ""), os.getenv("LLM_API_KEY", ""), os.getenv("LLM_MODEL", "")),
    }
    
    # 创建处理器
    processor = BatchDailyReportProcessor(max_days=3)
    
    # 运行处理
    result = processor.run(shared)
    print(f"处理结果: {result}")
