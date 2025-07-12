"""
ProcessPapersBatchNode - 批量处理论文节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.pdf_processor import process_paper_pdf
from daily_paper.utils.call_llm import call_llm
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def summarize_paper(paper_text):
    """
    论文摘要生成

    Args:
        paper_text: 论文文本

    Returns:
        摘要文本
    """
    prompt = f"用中文帮我介绍一下这篇文章: {paper_text}"
    return call_llm(prompt)


def process_single_paper(paper: ArxivPaper) -> tuple[str, str]:
    """
    处理单篇论文的完整流程：下载PDF + 生成摘要

    Args:
        paper: ArxivPaper对象

    Returns:
        tuple: (paper_id, summary_or_error_message)
    """
    try:
        # 下载PDF并提取文本
        logger.info(f"开始处理论文: {paper.paper_id}")
        paper_text = process_paper_pdf(paper.paper_url, paper.paper_id)

        if not paper_text:
            logger.warning(f"无法提取论文文本: {paper.paper_id}")
            return paper.paper_id, "无法提取论文文本"

        # 生成摘要
        summary = summarize_paper(paper_text)
        logger.info(f"已生成摘要: {paper.paper_id}")

        return paper.paper_id, summary

    except Exception as e:
        logger.error(f"处理论文失败 {paper.paper_id}: {str(e)}")
        return paper.paper_id, f"处理失败: {str(e)}"


class ParallelProcessPapersNode(Node):
    """批量处理论文节点（下载PDF+生成摘要）"""

    def __init__(self, max_workers=16, **kwargs):
        """
        初始化并行处理节点

        Args:
            max_workers: 最大并发线程数，默认16
        """
        super().__init__(**kwargs)
        self.max_workers = max_workers

    def prep(self, shared):
        """获取需要处理的论文列表"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取没有摘要的论文
        all_papers = paper_manager.get_all_papers()
        papers_without_summary = all_papers.loc[all_papers["summary"].isna()]

        # 转换为ArxivPaper对象列表
        papers = []
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
            papers.append(paper)

        logger.info(f"需要处理{len(papers)}篇论文，并发度: {self.max_workers}")
        return papers

    def exec(self, papers):
        """并行处理所有论文"""
        if not papers:
            logger.info("没有需要处理的论文")
            return []

        results = []

        # 使用ThreadPoolExecutor进行并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = [executor.submit(process_single_paper, paper) for paper in papers]

            # 收集结果
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Processing papers"
            ):
                try:
                    paper_id, summary = future.result()
                    results.append((paper_id, summary))
                    logger.info(f"完成处理论文 {paper_id}")
                except Exception as e:
                    logger.error(f"线程执行失败 {paper_id}: {str(e)}")
                    results.append((paper_id, f"线程执行失败: {str(e)}"))

        logger.info(f"并行处理完成，共处理{len(results)}篇论文")
        return results

    def post(self, shared, prep_res, exec_res):
        """保存处理结果"""
        if not exec_res:
            logger.info("没有处理结果需要保存")
            return "default"

        update_dict = {}
        for paper_id, summary in exec_res:
            update_dict[paper_id] = {
                "summary": summary,
            }

        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 更新DataFrame
        paper_manager.update_papers(update_dict)

        # 保存更新后的数据
        paper_manager.persist()

        shared["summaries"] = exec_res

        logger.info(f"批量更新了{len(exec_res)}篇论文摘要")
        return "default"
