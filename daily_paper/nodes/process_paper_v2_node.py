"""
ProcessPapersV2Node - 论文处理节点（V2版本）
支持基于模板的论文分析系统
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.pdf_processor import process_paper_pdf
from daily_paper.utils.call_llm import LLM
from daily_paper.templates import get_template, PaperAnalysisTemplate
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json
import yaml


def analyze_paper_with_template(
    paper_text: str, template: PaperAnalysisTemplate, llm: LLM
) -> str:
    """
    使用指定模板分析论文

    Args:
        paper_text: 论文文本
        template: 分析模板实例

    Returns:
        结构化分析结果（字符串形式，用于存储在summary字段）
    """
    prompt = template.generate_prompt(paper_text)
    response = llm.chat(prompt)
    return template.parse_response(response)


def analyze_paper_v2(paper_text, llm: LLM):
    """
    论文深度分析（V2版本）- 保持向后兼容性

    Args:
        paper_text: 论文文本

    Returns:
        结构化分析结果（字符串形式，用于存储在summary字段）
    """
    # 默认使用V2模板保持向后兼容
    template = get_template("v2")
    return analyze_paper_with_template(paper_text, template, llm)


def process_single_paper_with_generator(
    paper: ArxivPaper, summary_generator, llm: LLM
) -> tuple[str, str]:
    """
    处理单篇论文的完整流程：下载PDF + 使用自定义generator生成摘要

    Args:
        paper: ArxivPaper对象
        summary_generator: 摘要生成函数

    Returns:
        tuple: (paper_id, summary_or_error_message)
    """
    logger.info(f"开始处理论文: {paper.paper_id}")
    paper_text = process_paper_pdf(paper.paper_url, paper.paper_id)

    # 使用自定义generator生成摘要
    summary = summary_generator(paper_text, llm)
    logger.info(f"已生成摘要: {paper.paper_id}")

    return paper.paper_id, summary


class ProcessPapersV2Node(Node):
    """
    论文处理节点（V2版本）

    支持基于模板的论文分析系统
    """

    def __init__(self, template_name="v2", max_workers=16, **kwargs):
        """
        初始化并行处理节点

        Args:
            template_name: 分析模板名称，默认"v2"
            summary_generator: 自定义摘要生成函数，如果提供则忽略template_name
            max_workers: 最大并发线程数，默认16
        """
        super().__init__(**kwargs)
        self.template_name = template_name
        self.max_workers = max_workers

        try:
            template = get_template(template_name)
            self.summary_generator = lambda paper_text, llm: analyze_paper_with_template(
                paper_text, template, llm
            )
            logger.info(f"使用模板: {template_name} ({template.description})")
        except ValueError as e:
            logger.error(f"模板错误: {e}")
            # 回退到默认V2模板
            template = get_template("v2")
            self.summary_generator = lambda paper_text, llm: analyze_paper_with_template(
                paper_text, template, llm
            )
            logger.warning("回退到默认V2模板")

    def prep(self, shared):
        """获取需要处理的论文列表"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取没有摘要且未被过滤的论文
        all_papers = paper_manager.get_all_papers()
        # 处理filtered_out列可能为None的情况
        if "filtered_out" in all_papers.columns:
            all_papers["filtered_out"] = all_papers["filtered_out"].fillna(False)
        else:
            all_papers["filtered_out"] = False
        
        papers_without_summary = all_papers.loc[
            (all_papers["summary"].isna()) & (~all_papers["filtered_out"])
        ]

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
        if hasattr(self, "template_name"):
            logger.info(f"使用分析模板: {self.template_name}")
        else:
            logger.info(f"使用摘要生成器: {self.summary_generator.__name__}")
        # 从 shared 获取 LLM 实例
        llm: LLM = shared.get("llm")
        if llm is None:
            raise RuntimeError("LLM instance not found in shared store. Please set shared['llm'] before running.")
        return papers, llm

    def exec(self, prep_res):
        """并行处理所有论文"""
        papers, llm = prep_res
        if not papers:
            logger.info("没有需要处理的论文")
            return []

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    process_single_paper_with_generator, paper, self.summary_generator, llm
                )
                for paper in papers
            ]

            failed_results = []
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Processing papers"
            ):
                try:
                    paper_id, summary = future.result()
                    results.append((paper_id, summary))
                    logger.info(f"完成处理论文 {paper_id}")
                except Exception as e:
                    logger.error(f"处理失败: {str(e)}")
                    failed_results.append(str(e))
                    # skip adding this paper to results

        logger.info(f"并行处理完成，共处理{len(results)}篇论文")
        logger.info(f"失败论文: {failed_results}")
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
                "template": self.template_name,  # 记录使用的模板名称
            }

        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 更新DataFrame
        paper_manager.update_papers(update_dict)

        # 保存更新后的数据
        paper_manager.persist()

        shared["summaries"] = exec_res

        logger.info(f"批量更新了{len(exec_res)}篇论文摘要，使用模板: {self.template_name}")
        return "default"
