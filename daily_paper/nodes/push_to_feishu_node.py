"""
PushToFeishuNode - 推送论文到飞书节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import Node
from daily_paper.utils.arxiv_client import ArxivPaper
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.feishu_client import send_paper_to_feishu

from typing import Callable


def is_valid_summary(summary) -> bool:
    """检查summary是否有效（不为空且有实际内容）"""
    # 检查是否为None或NaN
    if summary is None or pd.isna(summary):
        return False

    # 转换为字符串并检查内容
    summary_str = str(summary).strip()
    return summary_str != "" and summary_str != "None"


class PushToFeishuNode(Node):
    """推送论文到飞书节点"""

    def __init__(self, summary_formatter: Callable = None, **kwargs):
        super().__init__(**kwargs)
        self.summary_formatter = summary_formatter

    def prep(self, shared):
        """获取需要推送的论文"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取有摘要但未推送的论文
        all_papers = paper_manager.get_all_papers()
        to_push = all_papers.loc[
            all_papers["summary"].apply(is_valid_summary)
            & (all_papers["pushed"] == False)
        ]

        # 按时间排序（旧到新）
        sorted_df = to_push.sort_values("update_time", ascending=True)

        # 转换为推送任务列表
        tasks = []
        for index, row in sorted_df.iterrows():
            paper = ArxivPaper(
                paper_id=row["paper_id"],
                paper_title=row["paper_title"],
                paper_url=row["paper_url"],
                paper_abstract=row["paper_abstract"],
                paper_authors=row["paper_authors"],
                paper_first_author=row["paper_first_author"],
                primary_category=row["primary_category"],
                publish_time=row["publish_time"],
                update_time=row["update_time"],
                comments=row["comments"],
            )
            tasks.append((paper, row["summary"]))

        logger.info(f"需要推送{len(tasks)}篇论文")
        return tasks

    def exec(self, tasks):
        """批量推送论文"""
        if not tasks:
            return []

        success_paper_ids = []

        for paper, summary in tasks:
            try:
                formatted_summary = (
                    self.summary_formatter(summary)
                    if self.summary_formatter
                    else summary
                )
                if send_paper_to_feishu(paper, formatted_summary):
                    success_paper_ids.append(paper.paper_id)
                    logger.info(f"推送成功: {paper.paper_id}")
                else:
                    logger.error(f"推送失败: {paper.paper_id}")
            except Exception as e:
                logger.error(f"推送异常 {paper.paper_id}: {str(e)}")

        return success_paper_ids

    def post(self, shared, prep_res, exec_res):
        """更新推送状态"""
        success_paper_ids = exec_res

        if not success_paper_ids:
            logger.info("没有成功推送的论文")
            return "default"

        # 更新推送状态
        paper_manager: PaperMetaManager = shared.get("paper_manager")
        update_dict = {}
        for paper_id in success_paper_ids:
            update_dict[paper_id] = {
                "pushed": True,
            }
        paper_manager.update_papers(update_dict)
        paper_manager.persist()

        shared["push_results"] = success_paper_ids

        logger.info(f"成功推送{len(success_paper_ids)}篇论文")
        return "default"
