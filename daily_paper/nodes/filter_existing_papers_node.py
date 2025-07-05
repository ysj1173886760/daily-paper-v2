"""
FilterExistingPapersNode - 过滤已存在论文节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.utils.data_manager import filter_new_papers

class FilterExistingPapersNode(Node):
    """过滤已存在论文节点"""
    
    def prep(self, shared):
        """从共享存储中读取论文数据和文件路径"""
        raw_papers = shared.get("raw_papers", {})
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        return raw_papers, meta_file
    
    def exec(self, prep_res):
        """过滤已存在的论文"""
        raw_papers, meta_file = prep_res
        if not raw_papers:
            logger.info("没有新论文需要过滤")
            return {}
        
        new_papers = filter_new_papers(raw_papers, meta_file)
        logger.info(f"过滤后剩余{len(new_papers)}篇新论文")
        return new_papers
    
    def post(self, shared, prep_res, exec_res):
        """将过滤后的论文保存到共享存储"""
        shared["new_papers"] = exec_res
        return "default" 