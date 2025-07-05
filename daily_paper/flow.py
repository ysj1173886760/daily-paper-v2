"""
Daily Paper Processing Flow

定义论文处理的完整流程
"""

from pocketflow import Flow
from .nodes import (
    FetchPapersNode, FilterExistingPapersNode, SavePapersNode,
    ProcessPapersBatchNode, PushToFeishuNode, GenerateDailyReportNode
)
from .utils.call_llm import setup_dspy_lm
import logging

def create_daily_paper_flow():
    """
    创建日报处理流程
    
    流程：
    1. 获取论文数据 (FetchPapersNode)
    2. 过滤已存在的论文 (FilterExistingPapersNode)
    3. 保存新论文数据 (SavePapersNode)
    4. 批量处理论文 (ProcessPapersBatchNode)
    5. 推送论文到飞书 (PushToFeishuNode)
    6. 生成并推送日报 (GenerateDailyReportNode)
    
    Returns:
        配置好的Flow对象
    """
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

def create_rag_paper_flow():
    """
    创建RAG论文处理流程
    
    Returns:
        配置好的Flow对象，专门处理RAG相关论文
    """
    flow = create_daily_paper_flow()
    
    # 设置RAG相关的默认参数
    flow.set_params({
        "query": "\"RAG\" OR \"Retrieval-Augmented Generation\"",
        "max_results": 40,
        "meta_file": "data/daily_papers.parquet"
    })
    
    logging.info("RAG Paper Processing Flow 创建完成")
    return flow

def create_kg_paper_flow():
    """
    创建知识图谱论文处理流程
    
    Returns:
        配置好的Flow对象，专门处理知识图谱相关论文
    """
    flow = create_daily_paper_flow()
    
    # 设置知识图谱相关的默认参数
    flow.set_params({
        "query": "\"knowledge-graph\" OR \"knowledge graph\"",
        "max_results": 40,
        "meta_file": "data/daily_papers_kg.parquet"
    })
    
    logging.info("KG Paper Processing Flow 创建完成")
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
        # 设置dspy LM
        lm = setup_dspy_lm()
        
        # 创建共享存储
        shared = {
            "query_params": {
                "query": query,
                "max_results": max_results,
                "meta_file": meta_file
            },
            "lm": lm,
            "raw_papers": {},
            "new_papers": {},
            "processed_papers": None,
            "summaries": {},
            "push_results": [],
            "daily_report": None,
            "daily_report_sent": False
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
        logging.info(f"日报推送: {'成功' if shared.get('daily_report_sent') else '失败'}")
        
        return shared
        
    except Exception as e:
        logging.error(f"流程执行失败: {str(e)}")
        raise

def run_rag_papers():
    """运行RAG论文处理流程"""
    return run_daily_paper_flow(
        "\"RAG\" OR \"Retrieval-Augmented Generation\"",
        5,
        "data/daily_papers.parquet"
    )

def run_kg_papers():
    """运行知识图谱论文处理流程"""
    return run_daily_paper_flow(
        "\"knowledge-graph\" OR \"knowledge graph\"",
        40,
        "data/daily_papers_kg.parquet"
    )

# 为了兼容性，提供旧版本的函数接口
def main(query: str, max_results: int, meta_file: str, lm):
    """
    主流程函数（兼容旧版本接口）
    
    Args:
        query: 搜索查询
        max_results: 最大结果数
        meta_file: 元数据文件路径
        lm: dspy LM对象
    """
    # 创建共享存储
    shared = {
        "query_params": {
            "query": query,
            "max_results": max_results,
            "meta_file": meta_file
        },
        "lm": lm,
        "raw_papers": {},
        "new_papers": {},
        "processed_papers": None,
        "summaries": {},
        "push_results": [],
        "daily_report": None,
        "daily_report_sent": False
    }
    
    # 创建并运行流程
    flow = create_daily_paper_flow()
    flow.run(shared)
    
    return shared

# 导出函数
__all__ = [
    "create_daily_paper_flow",
    "create_rag_paper_flow", 
    "create_kg_paper_flow",
    "run_daily_paper_flow",
    "run_rag_papers",
    "run_kg_papers",
    "main"
] 