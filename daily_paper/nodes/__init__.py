"""
Daily Paper Processing Nodes

包含所有论文处理相关的Node定义
"""

from .fetch_papers_node import FetchPapersNode
from .filter_existing_papers_node import FilterExistingPapersNode
from .process_papers_batch_node import ParallelProcessPapersNode
from .process_paper_v2_node import ProcessPapersV2Node
from .push_to_feishu_node import PushToFeishuNode
from .generate_daily_report_node import GenerateDailyReportNode

__all__ = [
    "FetchPapersNode",
    "FilterExistingPapersNode",
    "ParallelProcessPapersNode",
    "ProcessPapersV2Node",
    "PushToFeishuNode",
    "GenerateDailyReportNode",
]
