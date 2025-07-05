"""
FetchPapersNode - 获取论文数据节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.utils.arxiv_client import get_daily_papers
from daily_paper.utils.logger import logger


class FetchPapersNode(Node):
    """获取论文数据节点"""

    def prep(self, shared):
        """从共享存储中读取查询参数"""
        query_params = shared.get("query_params", {})
        return query_params.get("query", ""), query_params.get("max_results", 10)

    def exec(self, prep_res):
        """调用arXiv API获取论文"""
        query, max_results = prep_res
        if not query:
            logger.warning("查询参数为空")
            return {}

        logger.info(f"开始获取论文: {query}, 最大结果数: {max_results}")
        papers = get_daily_papers(query, max_results)
        logger.info(f"获取到{len(papers)}篇论文")
        return papers

    def post(self, shared, prep_res, exec_res):
        """将获取的论文保存到共享存储"""
        shared["raw_papers"] = exec_res
        return "default"
