"""
ArXiv API Client

封装arXiv API调用功能
"""

import arxiv
from daily_paper.utils.logger import logger
from daily_paper.model.arxiv_paper import ArxivPaper

ARXIV_URL = "http://arxiv.org/"


def get_daily_papers(query: str, max_results: int) -> dict[str, ArxivPaper]:
    """
    从arXiv获取论文数据

    Args:
        query: 搜索查询语句
        max_results: 最大结果数量

    Returns:
        以paper_key为key的论文字典
    """
    paper_result = {}
    search_engine = arxiv.Search(
        query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate
    )

    for result in search_engine.results():
        paper_id = result.get_short_id()
        paper_title = result.title
        paper_url = result.entry_id
        paper_abstract = result.summary.replace("\n", " ")
        paper_authors = get_authors(result.authors)
        paper_first_author = get_authors(result.authors, first_author=True)
        primary_category = result.primary_category
        publish_time = result.published.date()
        update_time = result.updated.date()
        comments = result.comment

        logger.debug(
            f"Time = {update_time} title = {paper_title} author = {paper_first_author}"
        )

        # eg: 2108.09112v1 -> 2108.09112
        ver_pos = paper_id.find("v")
        if ver_pos == -1:
            paper_key = paper_id
        else:
            paper_key = paper_id[0:ver_pos]
        paper_url = ARXIV_URL + "abs/" + paper_key

        arxiv_paper = ArxivPaper(
            paper_id=paper_id,
            paper_title=paper_title,
            paper_url=paper_url,
            paper_abstract=paper_abstract,
            paper_authors=paper_authors,
            paper_first_author=paper_first_author,
            primary_category=primary_category,
            publish_time=publish_time,
            update_time=update_time,
            comments=comments,
        )
        paper_result[paper_key] = arxiv_paper

    return paper_result


if __name__ == "__main__":
    # 测试函数
    papers = get_daily_papers('"RAG"', 5)
    print(f"获取到{len(papers)}篇论文")
    for paper_key, paper in papers.items():
        print(f"{paper_key}: {paper['paper_title']}")
