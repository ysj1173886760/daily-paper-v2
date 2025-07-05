"""
PushToFeishuNode - 推送论文到飞书节点
"""

from daily_paper.utils.logger import logger
import pandas as pd
from pocketflow import Node
from daily_paper.utils.arxiv_client import ArxivPaper
from daily_paper.utils.data_manager import get_unpushed_papers_with_summary, update_push_status
from daily_paper.utils.feishu_client import send_paper_to_feishu

class PushToFeishuNode(Node):
    """推送论文到飞书节点"""
    
    def prep(self, shared):
        """获取需要推送的论文"""
        df = shared.get("processed_papers", pd.DataFrame())
        
        if df.empty:
            return []
        
        # 获取有摘要但未推送的论文
        to_push = get_unpushed_papers_with_summary(df)
        
        if to_push.empty:
            logger.info("没有需要推送的论文")
            return []
        
        # 按时间排序（旧到新）
        sorted_df = to_push.sort_values('update_time', ascending=True)
        
        # 转换为推送任务列表
        tasks = []
        for index, row in sorted_df.iterrows():
            paper = ArxivPaper(
                paper_id=row['paper_id'],
                paper_title=row['paper_title'],
                paper_url=row['paper_url'],
                paper_abstract=row['paper_abstract'],
                paper_authors=row['paper_authors'],
                paper_first_author=row['paper_first_author'],
                primary_category=row['primary_category'],
                publish_time=row['publish_time'],
                update_time=row['update_time'],
                comments=row['comments']
            )
            tasks.append((index, paper, row['summary']))
        
        logger.info(f"需要推送{len(tasks)}篇论文")
        return tasks
    
    def exec(self, tasks):
        """批量推送论文"""
        if not tasks:
            return []
        
        success_indices = []
        
        for index, paper, summary in tasks:
            try:
                if send_paper_to_feishu(paper, summary):
                    success_indices.append(index)
                    logger.info(f"推送成功: {paper['paper_id']}")
                else:
                    logger.error(f"推送失败: {paper['paper_id']}")
            except Exception as e:
                logger.error(f"推送异常 {paper['paper_id']}: {str(e)}")
        
        return success_indices
    
    def post(self, shared, prep_res, exec_res):
        """更新推送状态"""
        success_indices = exec_res
        
        if not success_indices:
            logger.info("没有成功推送的论文")
            return "default"
        
        # 更新推送状态
        df = shared.get("processed_papers", pd.DataFrame())
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        
        df = update_push_status(df, success_indices, meta_file)
        shared["processed_papers"] = df
        shared["push_results"] = success_indices
        
        logger.info(f"成功推送{len(success_indices)}篇论文")
        return "default" 