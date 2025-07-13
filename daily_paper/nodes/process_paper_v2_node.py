"""
ProcessPapersV2Node - 论文处理节点（V2版本）
复用ParallelProcessPapersNode的代码结构，支持自定义summary generator
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
import json
import yaml


def analyze_paper_v2(paper_text):
    """
    论文深度分析（V2版本）- 作为自定义summary generator

    Args:
        paper_text: 论文文本

    Returns:
        结构化分析结果（字符串形式，用于存储在summary字段）
    """
    prompt = f"""
请仔细阅读以下论文内容，并回答下列问题，用中文回答：

论文内容：
{paper_text}

请按照以下格式回答，每个问题用一个单独的字段表示：

```yaml
problem: |
  论文要解决的是什么样的问题
background: |
  前人是怎么研究这个问题的，现在水平如何
idea_source: |
  这篇论文的idea从哪里来
solution: |
  论文的具体方案是什么
experiment: |
  论文是怎么设计实验来验证方案效果的
conclusion: |
  这篇论文能得出什么样的结论
future_work: |
  相关工作未来还有哪些思路
pseudocode: |
  用伪代码描述一下论文的核心思想
```

请确保输出格式严格按照上述YAML格式，每个字段都要填写完整。
"""

    response = call_llm(prompt)

    # 提取YAML部分
    yaml_start = response.find("```yaml")
    yaml_end = response.find("```", yaml_start + 7)

    if yaml_start != -1 and yaml_end != -1:
        yaml_content = response[yaml_start + 7 : yaml_end].strip()

        # 解析YAML验证格式
        analysis = yaml.safe_load(yaml_content)

        # 验证所有必需字段都存在
        required_fields = [
            "problem",
            "background",
            "idea_source",
            "solution",
            "experiment",
            "conclusion",
            "future_work",
            "pseudocode",
        ]

        for field in required_fields:
            if field not in analysis:
                analysis[field] = "分析不完整"

        return yaml_content

    else:
        logger.error("未找到YAML格式的回答")
        raise Exception("未找到YAML格式的回答")


def process_single_paper_with_generator(
    paper: ArxivPaper, summary_generator
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

    if not paper_text:
        logger.warning(f"无法提取论文文本: {paper.paper_id}")
        return paper.paper_id, "无法提取论文文本"

    # 使用自定义generator生成摘要
    summary = summary_generator(paper_text)
    logger.info(f"已生成摘要: {paper.paper_id}")

    return paper.paper_id, summary


class ProcessPapersV2Node(Node):
    """
    论文处理节点（V2版本）

    复用ParallelProcessPapersNode的代码结构，支持自定义summary generator
    """

    def __init__(self, summary_generator=None, max_workers=16, **kwargs):
        """
        初始化并行处理节点

        Args:
            summary_generator: 自定义摘要生成函数，默认使用analyze_paper_v2
            max_workers: 最大并发线程数，默认16
        """
        super().__init__(**kwargs)
        self.summary_generator = summary_generator or analyze_paper_v2
        self.max_workers = max_workers

    def prep(self, shared):
        """获取需要处理的论文列表"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取没有摘要且未被过滤的论文
        all_papers = paper_manager.get_all_papers()
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
        logger.info(f"使用摘要生成器: {self.summary_generator.__name__}")
        return papers

    def exec(self, papers):
        """并行处理所有论文"""
        if not papers:
            logger.info("没有需要处理的论文")
            return []

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    process_single_paper_with_generator, paper, self.summary_generator
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
            }

        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 更新DataFrame
        paper_manager.update_papers(update_dict)

        # 保存更新后的数据
        paper_manager.persist()

        shared["summaries"] = exec_res

        logger.info(f"批量更新了{len(exec_res)}篇论文摘要")
        return "default"
