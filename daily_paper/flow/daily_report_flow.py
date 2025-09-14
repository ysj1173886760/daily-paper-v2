"""
Daily Report Flow

日报生成工作流
"""

import datetime
from pocketflow import Flow, Node
from daily_paper.nodes.fetch_yesterday_papers_node import FetchYesterdayPapersNode
from daily_paper.nodes.analyze_and_recommend_papers_node import AnalyzeAndRecommendPapersNode
from daily_paper.nodes.push_daily_report_to_feishu_node import PushDailyReportToFeishuNode
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.date_helper import get_yesterday_date, format_date_chinese
from daily_paper.utils.call_llm import LLM, AsyncLLM


def create_daily_report_flow(target_date: datetime.date = None, recommendation_count: int = 3) -> Flow:
    """
    创建日报生成流程
    
    Args:
        target_date: 目标日期，默认为昨天
        recommendation_count: 推荐论文数量，默认3篇
        
    Returns:
        配置好的Flow对象
    """
    target_date = target_date or get_yesterday_date()
    
    # 创建节点
    fetch_node = FetchYesterdayPapersNode(target_date=target_date)
    analyze_node = AnalyzeAndRecommendPapersNode(recommendation_count=recommendation_count)
    push_node = PushDailyReportToFeishuNode()
    
    # 创建一个简单的终止节点，用于处理没有论文的情况
    class NoPapersNode(Node):
        def exec(self, prep_res):
            logger.info("没有论文可分析，流程结束")
            return "end"
    
    no_papers_node = NoPapersNode()
    
    # 连接节点
    fetch_node - "default" >> analyze_node  # 有论文时继续分析
    fetch_node - "no_papers" >> no_papers_node  # 没有论文时结束
    analyze_node >> push_node  # 分析完成后推送
    
    # 创建流程
    flow = Flow(start=fetch_node)
    
    logger.info(f"Daily Report Flow 创建完成，目标日期: {format_date_chinese(target_date)}")
    return flow


def run_daily_report_flow(
    meta_file_path: str,
    target_date: datetime.date = None,
    recommendation_count: int = 3,
    *,
    llm: LLM,
    async_llm: AsyncLLM | None = None,
) -> dict:
    """
    运行日报生成流程
    
    Args:
        meta_file_path: 论文元数据文件路径
        target_date: 目标日期，默认为昨天
        recommendation_count: 推荐论文数量，默认3篇
        
    Returns:
        包含执行结果的shared字典
    """
    target_date = target_date or get_yesterday_date()
    
    logger.info(f"开始运行日报生成流程，目标日期: {format_date_chinese(target_date)}")
    
    try:
        # 初始化shared store
        shared = {
            "paper_manager": PaperMetaManager(meta_file_path),
            "target_date": target_date,
            "llm": llm,
            "async_llm": async_llm,
        }
        
        # 创建并运行流程
        flow = create_daily_report_flow(target_date, recommendation_count)
        flow.run(shared)
        
        # 记录执行结果
        papers_count = len(shared.get("yesterday_papers", []))
        recommendations_count = len(shared.get("analysis_and_recommendations", {}).get("recommendations", []))
        push_success = shared.get("push_result", {}).get("success", False)
        
        logger.info(f"日报流程执行完成:")
        logger.info(f"  - 论文数量: {papers_count}")
        logger.info(f"  - 推荐数量: {recommendations_count}")
        logger.info(f"  - 推送状态: {'成功' if push_success else '失败'}")
        
        return shared
        
    except Exception as e:
        logger.error(f"日报流程执行失败: {str(e)}")
        raise


def run_daily_report_with_config(config, target_date: datetime.date = None):
    """
    使用配置对象运行日报流程
    
    Args:
        config: 配置对象，包含meta_file_path等信息
        target_date: 目标日期，默认为昨天
    """
    recommendation_count = getattr(config, "daily_report_recommendation_count", 3)
    
    # 构建 LLM 实例
    llm = LLM(config.llm_base_url, config.llm_api_key, config.llm_model)
    async_llm = AsyncLLM(config.llm_base_url, config.llm_api_key, config.llm_model)

    return run_daily_report_flow(
        meta_file_path=config.meta_file_path,
        target_date=target_date,
        recommendation_count=recommendation_count,
        llm=llm,
        async_llm=async_llm,
    )


# 导出函数
__all__ = [
    "create_daily_report_flow",
    "run_daily_report_flow", 
    "run_daily_report_with_config"
]


if __name__ == "__main__":
    # 测试日报流程
    from daily_paper.config import Config
    
    # 使用默认配置测试
    config = Config.from_yaml("config/rag.yaml")
    
    try:
        result = run_daily_report_with_config(config)
        print("日报生成测试完成")
        print(f"处理论文数: {len(result.get('yesterday_papers', []))}")
        
        push_result = result.get("push_result", {})
        if push_result.get("success"):
            print("推送成功")
        else:
            print(f"推送失败: {push_result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
