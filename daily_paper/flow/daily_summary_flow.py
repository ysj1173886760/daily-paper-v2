"""
Daily Summary Flow

每日汇总工作流 - 处理历史未推送的日报
"""

import datetime
from pocketflow import Flow
from daily_paper.nodes.get_next_pending_date_node import GetNextPendingDateNode
from daily_paper.nodes.fetch_yesterday_papers_node import FetchYesterdayPapersNode
from daily_paper.nodes.analyze_and_recommend_papers_node import AnalyzeAndRecommendPapersNode
from daily_paper.nodes.push_daily_report_to_feishu_node import PushDailyReportToFeishuNode
from daily_paper.nodes.update_push_status_node import UpdatePushStatusNode
from daily_paper.nodes.handle_no_papers_node import HandleNoPapersNode
from daily_paper.utils.logger import logger


class DailySummaryFlow(Flow):
    """每日汇总工作流 - 逐日处理历史未推送的日报"""
    
    def __init__(self, tracker_file: str = "data/report_tracker.json"):
        """
        初始化工作流
        
        Args:
            tracker_file: 跟踪文件路径
        """
        self.tracker_file = tracker_file
        
        # 创建节点
        self.get_next_date_node = GetNextPendingDateNode(tracker_file=tracker_file)
        self.fetch_papers_node = FetchYesterdayPapersNode()
        self.analyze_node = AnalyzeAndRecommendPapersNode()
        self.push_node = PushDailyReportToFeishuNode()
        self.update_status_node = UpdatePushStatusNode()
        self.handle_no_papers_node = HandleNoPapersNode()
        
        # 设置工作流连接
        self._setup_flow()
        
        # 初始化Flow
        super().__init__(start=self.get_next_date_node)
    
    def _setup_flow(self):
        """设置工作流连接"""
        # 有待处理日期时的正常流程
        self.get_next_date_node - "has_pending" >> self.fetch_papers_node
        
        # 有论文时继续分析推送
        self.fetch_papers_node - "default" >> self.analyze_node
        self.analyze_node >> self.push_node
        self.push_node >> self.update_status_node
        
        # 没有论文时处理无论文情况
        self.fetch_papers_node - "no_papers" >> self.handle_no_papers_node
        
    def prep(self, shared):
        """Flow的准备阶段：验证必需的数据"""
        if "paper_manager" not in shared:
            raise ValueError("paper_manager must be provided in shared store")
        
        logger.info("开始每日汇总工作流")
        return None
    
    def post(self, shared, prep_res, exec_res):
        """Flow的后处理阶段：记录结果"""
        next_pending_result = shared.get("next_pending_result", {})
        
        if next_pending_result.get("has_pending"):
            processed_date = shared.get("target_date")
            push_result = shared.get("push_result", {})
            
            if push_result.get("success"):
                logger.info(f"成功处理并推送了日期 {processed_date} 的日报")
            else:
                logger.warning(f"处理日期 {processed_date} 的日报失败")
        else:
            logger.info("没有待处理的日期，所有日报已是最新")
        
        return "completed"


class DailySummaryRunner:
    """每日汇总运行器"""
    
    def __init__(self, tracker_file: str = "data/report_tracker.json"):
        """
        初始化运行器
        
        Args:
            tracker_file: 跟踪文件路径
        """
        self.tracker_file = tracker_file
    
    def run_single(self, shared: dict) -> dict:
        """
        运行单次每日汇总（处理一个日期）
        
        Args:
            shared: 共享数据存储，必须包含 paper_manager
            
        Returns:
            处理结果
        """
        logger.info("开始单次每日汇总处理")
        
        try:
            # 创建并运行工作流
            flow = DailySummaryFlow(tracker_file=self.tracker_file)
            result = flow.run(shared)
            
            # 检查处理结果
            next_pending_result = shared.get("next_pending_result", {})
            push_result = shared.get("push_result", {})
            status_update_result = shared.get("status_update_result", {})
            
            return {
                "success": True,
                "has_pending": next_pending_result.get("has_pending", False),
                "processed_date": shared.get("target_date"),
                "push_success": push_result.get("success", False),
                "status_updated": status_update_result.get("success", False),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"每日汇总处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "has_pending": False
            }
    
    def run_batch(self, shared: dict, max_days: int = 7) -> dict:
        """
        运行批量每日汇总（处理多个日期）
        
        Args:
            shared: 共享数据存储，必须包含 paper_manager
            max_days: 最多处理的天数
            
        Returns:
            批量处理结果
        """
        logger.info(f"开始批量每日汇总处理，最多处理 {max_days} 天")
        
        processed_days = 0
        results = []
        
        try:
            for day_count in range(max_days):
                logger.info(f"开始处理第 {day_count + 1} 天")
                
                # 运行单次处理
                result = self.run_single(shared)
                results.append(result)
                
                if not result["success"]:
                    logger.error(f"第 {day_count + 1} 天处理失败，停止批量处理")
                    break
                
                if not result["has_pending"]:
                    logger.info("没有更多待处理的日期，批量处理完成")
                    break
                
                # 如果连续处理同一个日期且失败，避免无限循环
                current_date = result.get("processed_date")
                if current_date and day_count > 0:
                    prev_date = results[day_count-1].get("processed_date") 
                    if current_date == prev_date and not result["push_success"]:
                        logger.warning(f"连续处理同一日期 {current_date} 且失败，停止处理避免循环")
                        break
                
                if result["push_success"]:
                    processed_days += 1
                    logger.info(f"第 {day_count + 1} 天处理成功，已处理 {processed_days} 天")
                else:
                    logger.warning(f"第 {day_count + 1} 天推送失败，但继续处理下一天")
            
            logger.info(f"批量每日汇总处理完成，共成功处理 {processed_days} 天")
            
            return {
                "success": True,
                "total_processed": processed_days,
                "total_attempted": len(results),
                "max_days": max_days,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"批量每日汇总处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_processed": processed_days,
                "total_attempted": len(results),
                "results": results
            }


if __name__ == "__main__":
    # 测试每日汇总工作流
    from daily_paper.utils.data_manager import PaperMetaManager
    
    # 创建测试用的shared数据
    shared = {
        "paper_manager": PaperMetaManager("data/papers.parquet")
    }
    
    # 测试单次运行
    runner = DailySummaryRunner()
    
    print("=== 测试单次运行 ===")
    single_result = runner.run_single(shared)
    print(f"单次处理结果: {single_result}")
    
    print("\n=== 测试批量运行 ===")
    batch_result = runner.run_batch(shared, max_days=3)
    print(f"批量处理结果: {batch_result}")