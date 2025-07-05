"""
Daily Paper Processing Flow

定义论文处理的完整流程
"""

from pocketflow import Flow
from .nodes import (
    FetchPapersNode,
    FilterExistingPapersNode,
    SavePapersNode,
    ProcessPapersBatchNode,
    PushToFeishuNode,
    GenerateDailyReportNode,
)
import logging


def create_daily_paper_flow() -> Flow:
    # 创建所有节点
    fetch_node = FetchPapersNode()
    filter_node = FilterExistingPapersNode()
    save_node = SavePapersNode()
    process_node = ProcessPapersBatchNode()
    push_node = PushToFeishuNode()
    report_node = GenerateDailyReportNode()

    # 连接节点形成流水线
    fetch_node >> filter_node >> save_node >> process_node >> push_node >> report_node

    # 创建Flow对象
    flow = Flow(start=fetch_node)

    logging.info("Daily Paper Processing Flow 创建完成")
    return flow


def run_daily_paper_flow(query: str, max_results: int, meta_file: str):
    """
    运行日报处理流程

    Args:
        query: 搜索查询
        max_results: 最大结果数
        meta_file: 元数据文件路径
    """
    try:
        # 创建共享存储
        shared = {
            "query_params": {
                "query": query,
                "max_results": max_results,
                "meta_file": meta_file,
            },
            "raw_papers": {},
            "new_papers": {},
            "processed_papers": None,
            "summaries": {},
            "push_results": [],
            "daily_report": None,
            "daily_report_sent": False,
        }

        # 创建并运行流程
        flow = create_daily_paper_flow()
        flow.run(shared)

        # 输出结果摘要
        logging.info("=== 流程执行完成 ===")
        logging.info(f"原始论文数: {len(shared.get('raw_papers', {}))}")
        logging.info(f"新论文数: {len(shared.get('new_papers', {}))}")
        logging.info(f"处理摘要数: {len(shared.get('summaries', {}))}")
        logging.info(f"推送成功数: {len(shared.get('push_results', []))}")
        logging.info(f"日报推送: {'成功' if shared.get('daily_report_sent') else '失败/无日报'}")

        return shared

    except Exception as e:
        logging.error(f"流程执行失败: {str(e)}")
        raise


def run_rag_papers():
    """运行RAG论文处理流程"""
    return run_daily_paper_flow(
        '"RAG" OR "Retrieval-Augmented Generation"', 5, "data/daily_papers.parquet"
    )


def run_kg_papers():
    """运行知识图谱论文处理流程"""
    return run_daily_paper_flow(
        '"knowledge-graph" OR "knowledge graph"', 40, "data/daily_papers_kg.parquet"
    )


# 导出函数
__all__ = [
    "create_daily_paper_flow",
    "run_daily_paper_flow",
    "run_rag_papers",
    "run_kg_papers",
]
