"""
Daily Paper Processing Nodes

包含所有论文处理相关的Node定义
"""

from .fetch_papers_node import FetchPapersNode
from .filter_existing_papers_node import FilterExistingPapersNode
from .filter_irrelevant_papers_node import FilterIrrelevantPapersNode
from .process_paper_v2_node import ProcessPapersV2Node
from .push_to_feishu_node import PushToFeishuNode
# from .generate_daily_report_node import GenerateDailyReportNode  # 暂时注释，避免与新的日报功能冲突
from .generate_html_node import GenerateHTMLNode
from .publish_rss_node import PublishRSSNode
from .deploy_github_node import DeployGitHubNode
from .fetch_yesterday_papers_node import FetchYesterdayPapersNode
from .analyze_and_recommend_papers_node import AnalyzeAndRecommendPapersNode
from .push_daily_report_to_feishu_node import PushDailyReportToFeishuNode

__all__ = [
    "FetchPapersNode",
    "FilterExistingPapersNode",
    "FilterIrrelevantPapersNode",
    "ProcessPapersV2Node",
    "PushToFeishuNode",
    # "GenerateDailyReportNode",  # 暂时注释
    "GenerateHTMLNode",
    "PublishRSSNode",
    "DeployGitHubNode",
    "FetchYesterdayPapersNode",
    "AnalyzeAndRecommendPapersNode",
    "PushDailyReportToFeishuNode",
]
