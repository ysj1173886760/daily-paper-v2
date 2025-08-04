"""
Fetch Yesterday Papers Node

获取昨日论文的节点
"""

import datetime
from typing import List
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger
from daily_paper.utils.date_helper import get_yesterday_date, format_date_chinese
from daily_paper.utils.data_manager import is_valid_summary


class FetchYesterdayPapersNode(Node):
    """获取昨日论文的节点"""
    
    def __init__(self, target_date: datetime.date = None):
        """
        初始化节点
        
        Args:
            target_date: 目标日期，默认为昨天
        """
        super().__init__()
        self.target_date = target_date or get_yesterday_date()
    
    def prep(self, shared):
        """准备阶段：从shared获取paper_manager"""
        paper_manager = shared.get("paper_manager")
        if not paper_manager:
            raise ValueError("paper_manager not found in shared store")
        
        return {
            "paper_manager": paper_manager,
            "target_date": self.target_date
        }
    
    def exec(self, prep_res):
        """执行阶段：获取指定日期的论文并过滤有效摘要"""
        paper_manager = prep_res["paper_manager"]
        target_date = prep_res["target_date"]
        
        logger.info(f"开始获取 {format_date_chinese(target_date)} 的论文")
        
        # 获取指定日期的论文
        daily_papers_df = paper_manager.get_paper_by_day(target_date)
        
        if daily_papers_df.empty:
            logger.warning(f"{format_date_chinese(target_date)} 没有找到任何论文")
            return []
        
        # 转换为ArxivPaper对象列表
        papers = []
        for _, row in daily_papers_df.iterrows():
            paper = ArxivPaper(**row.to_dict())
            papers.append(paper)
        
        # 过滤出有有效summary的论文
        valid_papers = []
        for paper in papers:
            if is_valid_summary(paper.summary):
                valid_papers.append(paper)
            else:
                logger.debug(f"论文 {paper.paper_id} 缺少有效摘要，跳过")
        
        logger.info(f"获取到 {len(papers)} 篇论文，其中 {len(valid_papers)} 篇有有效摘要")
        
        return valid_papers
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：将结果存储到shared"""
        target_date = prep_res["target_date"]
        papers = exec_res
        
        # 存储到shared
        shared["target_date"] = target_date
        shared["yesterday_papers"] = papers
        
        logger.info(f"已将 {len(papers)} 篇 {format_date_chinese(target_date)} 的论文存储到shared")
        
        if not papers:
            logger.warning("没有有效论文，无法继续后续分析")
            return "no_papers"  # 返回特殊action表示没有论文
        
        return "default"  # 继续到下一个节点