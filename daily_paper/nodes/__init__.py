"""
Daily Paper Processing Nodes

包含所有论文处理相关的Node定义
"""

from .fetch_papers_node import FetchPapersNode
from .filter_existing_papers_node import FilterExistingPapersNode
from .filter_irrelevant_papers_node import FilterIrrelevantPapersNode
from .process_paper_v2_node import ProcessPapersV2Node
from .push_to_feishu_node import PushToFeishuNode
from .generate_daily_report_node import GenerateDailyReportNode
from .generate_html_node import GenerateHTMLNode
from .publish_rss_node import PublishRSSNode
from .deploy_github_node import DeployGitHubNode

__all__ = [
    "FetchPapersNode",
    "FilterExistingPapersNode",
    "FilterIrrelevantPapersNode",
    "ProcessPapersV2Node",
    "PushToFeishuNode",
    "GenerateDailyReportNode",
    "GenerateHTMLNode",
    "PublishRSSNode",
    "DeployGitHubNode",
]
