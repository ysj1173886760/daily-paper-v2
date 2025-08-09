"""
PushToFeishuNode - 推送论文到飞书节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import Node
from daily_paper.utils.arxiv_client import ArxivPaper
from daily_paper.utils.data_manager import PaperMetaManager, is_valid_summary
from daily_paper.utils.feishu_client import FeishuClient
from daily_paper.templates import get_template

from typing import Callable



class PushToFeishuNode(Node):
    """推送论文到飞书节点"""

    def __init__(self, summary_formatter: Callable = None, feishu_client: FeishuClient = None, **kwargs):
        super().__init__(**kwargs)
        self.summary_formatter = summary_formatter
        self.feishu_client = feishu_client

    def prep(self, shared):
        """获取需要推送的论文"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")
        config = shared.get("config")
        
        # 获取飞书客户端，优先级：传入的客户端 > 从配置创建 > 错误
        feishu_client = self.feishu_client
        if not feishu_client and config and hasattr(config, 'feishu_webhook_url') and config.feishu_webhook_url:
            feishu_client = FeishuClient(config.feishu_webhook_url)
        
        if not feishu_client:
            raise ValueError("飞书客户端未配置，请传入 feishu_client 或在 config 中设置 feishu_webhook_url")

        all_papers = paper_manager.get_all_papers()
        to_push = all_papers.loc[
            all_papers["summary"].apply(is_valid_summary)
            & (all_papers["pushed"] == False)
            & (~all_papers["filtered_out"])
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
            template_name = row.get("template", "v2")  # 获取模板名称，默认为v2
            tasks.append((paper, row["summary"], template_name))

        logger.info(f"需要推送{len(tasks)}篇论文")
        return {
            "tasks": tasks,
            "feishu_client": feishu_client
        }

    def exec(self, prep_res):
        """批量推送论文"""
        tasks = prep_res["tasks"]
        feishu_client = prep_res["feishu_client"]
        
        if not tasks:
            return []

        success_paper_ids = []

        for paper, summary, template_name in tasks:
            try:
                # 根据论文的模板名称获取对应的格式化器
                if self.summary_formatter:
                    # 优先使用传入的格式化器（向后兼容）
                    formatted_summary = self.summary_formatter(summary)
                else:
                    # 使用论文记录的模板进行格式化
                    try:
                        template = get_template(template_name)
                        formatted_summary = template.format_to_markdown(summary)
                        logger.debug(f"使用模板 {template_name} 格式化论文 {paper.paper_id}")
                    except ValueError as e:
                        logger.warning(f"模板 {template_name} 不存在，使用默认格式: {e}")
                        # 回退到默认模板
                        template = get_template("v2")
                        formatted_summary = template.format_to_markdown(summary)
                    except Exception as e:
                        logger.warning(f"模板格式化失败，使用原始内容: {e}")
                        formatted_summary = summary

                if feishu_client.send_paper(paper, formatted_summary):
                    success_paper_ids.append(paper.paper_id)
                    logger.info(f"推送成功: {paper.paper_id} (模板: {template_name})")
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
