"""
FilterExistingPapersNode - 过滤已存在论文节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.utils.data_manager import PaperMetaManager


class FilterExistingPapersNode(Node):
    """过滤已存在论文节点"""

    def prep(self, shared):
        """从共享存储中读取论文数据和文件路径"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")
        raw_papers = shared.get("raw_papers", {})
        return raw_papers, paper_manager

    def exec(self, prep_res):
        """过滤已存在的论文"""
        raw_papers = prep_res[0]
        paper_manager: PaperMetaManager = prep_res[1]
        if not raw_papers:
            logger.info("没有新论文需要过滤")
            return {}

        new_papers = paper_manager.filter_new_papers(raw_papers)
        logger.info(f"过滤出{len(new_papers)}篇新论文（原有{len(raw_papers)}篇）")
        return new_papers

    def post(self, shared, prep_res, exec_res):
        """将过滤后的论文保存到共享存储"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")
        paper_manager.set_paper(exec_res)

        shared["new_papers"] = exec_res

        return "default"
