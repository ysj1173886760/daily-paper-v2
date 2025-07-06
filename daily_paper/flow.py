from pocketflow import Flow
from .nodes import (
    FetchPapersNode,
    FilterExistingPapersNode,
    ProcessPapersBatchNode,
    PushToFeishuNode,
)
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager


def create_daily_paper_flow() -> Flow:
    # 创建所有节点
    fetch_node = FetchPapersNode()
    filter_node = FilterExistingPapersNode()
    process_node = ProcessPapersBatchNode()
    push_node = PushToFeishuNode()

    # 连接节点形成流水线
    fetch_node >> filter_node >> process_node >> push_node

    # 创建Flow对象
    flow = Flow(start=fetch_node)

    logger.info("Daily Paper Processing Flow 创建完成")
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
            },
            "paper_manager": PaperMetaManager(meta_file),
        }

        # 创建并运行流程
        flow = create_daily_paper_flow()
        flow.run(shared)

        # 输出结果摘要
        logger.info("=== 流程执行完成 ===")

        return shared

    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}")
        raise


def run_rag_papers():
    """运行RAG论文处理流程"""
    return run_daily_paper_flow(
        '"RAG" OR "Retrieval-Augmented Generation"', 7, "data/daily_papers.parquet"
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
