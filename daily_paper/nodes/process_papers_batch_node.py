"""
ProcessPapersBatchNode - 批量处理论文节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import BatchNode
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.pdf_processor import process_paper_pdf
from daily_paper.utils.call_llm import call_llm


def summarize_paper(paper_text):
    """
    论文摘要生成

    Args:
        lm: dspy LM对象
        paper_text: 论文文本

    Returns:
        摘要文本
    """
    prompt = f"用中文帮我介绍一下这篇文章: {paper_text}"
    return call_llm(prompt)


class ProcessPapersBatchNode(BatchNode):
    """批量处理论文节点（下载PDF+生成摘要）"""

    def prep(self, shared):
        """获取需要处理的论文列表"""
        lm = shared.get("lm")
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取没有摘要的论文
        all_papers = paper_manager.get_all_papers()
        papers_without_summary = all_papers.loc[all_papers["summary"].isna()]

        # 转换为处理任务列表
        tasks = []
        for index, row in papers_without_summary.iterrows():
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
            tasks.append((paper, lm))

        logger.info(f"需要处理{len(tasks)}篇论文")
        return tasks

    def exec(self, task):
        """处理单篇论文"""
        paper: ArxivPaper = task[0]
        lm = task[1]

        try:
            # 下载PDF并提取文本
            paper_text = process_paper_pdf(paper.paper_url, paper.paper_id)

            if not paper_text:
                logger.warning(f"无法提取论文文本: {paper.paper_id}")
                return paper.paper_id, "无法提取论文文本"

            # 生成摘要
            # summary = summarize_paper(paper_text)
            summary = " test"
            logger.info(f"已生成摘要: {paper.paper_id}")

            return paper.paper_id, summary

        except Exception as e:
            logger.error(f"处理论文失败 {paper.paper_id}: {str(e)}")
            return paper.paper_id, f"处理失败: {str(e)}"

    def post(self, shared, prep_res, exec_res_list):
        """更新论文摘要"""
        if not exec_res_list:
            logger.info("没有摘要需要更新")
            return "default"

        # 构建摘要字典
        update_dict = {}
        for paper_id, summary in exec_res_list:
            update_dict[paper_id] = {
                "summary": summary,
            }

        paper_manager: PaperMetaManager = shared.get("paper_manager")
        print(paper_manager.df)

        # 更新DataFrame
        paper_manager.update_papers(update_dict)

        # 保存更新后的数据
        paper_manager.persist()

        logger.info(f"批量更新了{len(exec_res_list)}篇论文摘要")
        return "default"
