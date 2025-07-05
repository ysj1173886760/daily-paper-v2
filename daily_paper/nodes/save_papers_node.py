"""
SavePapersNode - 保存论文数据节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.utils.data_manager import save_papers_to_parquet, load_papers_from_parquet

class SavePapersNode(Node):
    """保存论文数据节点"""
    
    def prep(self, shared):
        """从共享存储中读取新论文和文件路径"""
        new_papers = shared.get("new_papers", {})
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        return new_papers, meta_file
    
    def exec(self, prep_res):
        """保存论文到文件"""
        new_papers, meta_file = prep_res
        if not new_papers:
            logger.info("没有新论文需要保存")
            return True
        
        save_papers_to_parquet(new_papers, meta_file)
        return True
    
    def post(self, shared, prep_res, exec_res):
        """加载完整的论文数据"""
        _, meta_file = prep_res
        # 重新加载完整的论文数据
        df = load_papers_from_parquet(meta_file)
        shared["processed_papers"] = df
        return "default" 