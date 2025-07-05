"""
ProcessPapersBatchNode - 批量处理论文节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import BatchNode
from daily_paper.utils.arxiv_client import ArxivPaper
from daily_paper.utils.data_manager import (
    get_papers_without_summary,
    update_paper_summaries,
)
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
        df = shared.get("processed_papers", pd.DataFrame())
        lm = shared.get("lm")

        if df.empty:
            logger.info("没有论文需要处理")
            return []

        # 获取没有摘要的论文
        papers_without_summary = get_papers_without_summary(df)

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
            tasks.append((index, paper, lm))

        logger.info(f"需要处理{len(tasks)}篇论文")
        return tasks

    def exec(self, task):
        """处理单篇论文"""
        index, paper, lm = task

        try:
            # 下载PDF并提取文本
            paper_text = process_paper_pdf(paper["paper_url"], paper["paper_id"])

            if not paper_text:
                logger.warning(f"无法提取论文文本: {paper['paper_id']}")
                return index, "无法提取论文文本"

            # 生成摘要
            summary = summarize_paper(lm, paper_text)
            logger.info(f"已生成摘要: {paper['paper_id']}")

            return index, summary

        except Exception as e:
            logger.error(f"处理论文失败 {paper['paper_id']}: {str(e)}")
            return index, f"处理失败: {str(e)}"

    def post(self, shared, prep_res, exec_res_list):
        """更新论文摘要"""
        if not exec_res_list:
            logger.info("没有摘要需要更新")
            return "default"

        # 构建摘要字典
        summaries = {index: summary for index, summary in exec_res_list}

        # 更新DataFrame
        df = shared.get("processed_papers", pd.DataFrame())
        df = update_paper_summaries(df, summaries)

        # 保存更新后的数据
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        if meta_file:
            df.to_parquet(meta_file, engine="pyarrow")

        shared["processed_papers"] = df
        shared["summaries"] = summaries

        logger.info(f"批量更新了{len(summaries)}篇论文摘要")
        return "default"
