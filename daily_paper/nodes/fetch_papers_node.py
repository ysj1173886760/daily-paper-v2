"""
FetchPapersNode - 获取论文数据节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger
import arxiv

ARXIV_URL = "http://arxiv.org/"


def get_authors(authors, first_author=False):
    """提取作者信息"""
    if first_author:
        return str(authors[0])
    return ", ".join(str(author) for author in authors)


class FetchPapersNode(Node):
    def __init__(
        self, topic: str | list[str], search_offset: int = 0, search_limit: int = 100
    ):
        super().__init__()

        if isinstance(topic, list):
            self.topic = " OR ".join(f'"{t}"' for t in topic)
        else:
            self.topic = f'"{topic}"' if " OR " not in topic else topic
        self.search_offset = search_offset
        self.search_limit = search_limit
        self.arxiv_max_results = search_offset + search_limit

    def process_paper(self, result: arxiv.Result) -> ArxivPaper:
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
        return arxiv_paper

    def process_once(self) -> list[ArxivPaper]:
        paper_list = []

        client = arxiv.Client(num_retries=100)
        search = arxiv.Search(
            query=self.topic,
            max_results=self.arxiv_max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )

        for result in client.results(search, offset=self.search_offset):
            arxiv_paper = self.process_paper(result)
            paper_list.append(arxiv_paper)

            if len(paper_list) >= self.search_limit:
                break

        return paper_list

    def prep(self, shared):
        return {}

    def exec(self, prep_res):
        return self.process_once()

    def post(self, shared, prep_res, exec_res):
        """将获取的论文保存到共享存储"""
        shared["raw_papers"] = exec_res
        return "default"
