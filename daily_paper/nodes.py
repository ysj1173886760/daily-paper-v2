"""
Daily Paper Processing Nodes

包含所有论文处理相关的Node定义
"""

from pocketflow import Node, BatchNode
from typing import Dict, List, Any
import pandas as pd
import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 导入工具函数
from .utils.arxiv_client import get_daily_papers, ArxivPaper
from .utils.data_manager import (
    save_papers_to_parquet, load_papers_from_parquet, filter_new_papers,
    get_papers_without_summary, get_unpushed_papers_with_summary,
    update_paper_summaries, update_push_status, get_daily_papers as get_daily_papers_from_df
)
from .utils.pdf_processor import process_paper_pdf
from .utils.feishu_client import send_paper_to_feishu, send_daily_report_to_feishu
from .utils.call_llm import summarize_paper, generate_daily_summary

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
            logging.warning("查询参数为空")
            return {}
        
        logging.info(f"开始获取论文: {query}, 最大结果数: {max_results}")
        papers = get_daily_papers(query, max_results)
        logging.info(f"获取到{len(papers)}篇论文")
        return papers
    
    def post(self, shared, prep_res, exec_res):
        """将获取的论文保存到共享存储"""
        shared["raw_papers"] = exec_res
        return "default"

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
            logging.info("没有新论文需要过滤")
            return {}
        
        new_papers = filter_new_papers(raw_papers, meta_file)
        logging.info(f"过滤后剩余{len(new_papers)}篇新论文")
        return new_papers
    
    def post(self, shared, prep_res, exec_res):
        """将过滤后的论文保存到共享存储"""
        shared["new_papers"] = exec_res
        return "default"

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
            logging.info("没有新论文需要保存")
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

class ProcessPapersBatchNode(BatchNode):
    """批量处理论文节点（下载PDF+生成摘要）"""
    
    def prep(self, shared):
        """获取需要处理的论文列表"""
        df = shared.get("processed_papers", pd.DataFrame())
        lm = shared.get("lm")
        
        if df.empty:
            logging.info("没有论文需要处理")
            return []
        
        # 获取没有摘要的论文
        papers_without_summary = get_papers_without_summary(df)
        
        # 转换为处理任务列表
        tasks = []
        for index, row in papers_without_summary.iterrows():
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
            tasks.append((index, paper, lm))
        
        logging.info(f"需要处理{len(tasks)}篇论文")
        return tasks
    
    def exec(self, task):
        """处理单篇论文"""
        index, paper, lm = task
        
        try:
            # 下载PDF并提取文本
            paper_text = process_paper_pdf(paper['paper_url'], paper['paper_id'])
            
            if not paper_text:
                logging.warning(f"无法提取论文文本: {paper['paper_id']}")
                return index, "无法提取论文文本"
            
            # 生成摘要
            summary = summarize_paper(lm, paper_text)
            logging.info(f"已生成摘要: {paper['paper_id']}")
            
            return index, summary
            
        except Exception as e:
            logging.error(f"处理论文失败 {paper['paper_id']}: {str(e)}")
            return index, f"处理失败: {str(e)}"
    
    def post(self, shared, prep_res, exec_res_list):
        """更新论文摘要"""
        if not exec_res_list:
            logging.info("没有摘要需要更新")
            return "default"
        
        # 构建摘要字典
        summaries = {index: summary for index, summary in exec_res_list}
        
        # 更新DataFrame
        df = shared.get("processed_papers", pd.DataFrame())
        df = update_paper_summaries(df, summaries)
        
        # 保存更新后的数据
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        if meta_file:
            df.to_parquet(meta_file, engine='pyarrow')
        
        shared["processed_papers"] = df
        shared["summaries"] = summaries
        
        logging.info(f"批量更新了{len(summaries)}篇论文摘要")
        return "default"

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
            logging.info("没有需要推送的论文")
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
        
        logging.info(f"需要推送{len(tasks)}篇论文")
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
                    logging.info(f"推送成功: {paper['paper_id']}")
                else:
                    logging.error(f"推送失败: {paper['paper_id']}")
            except Exception as e:
                logging.error(f"推送异常 {paper['paper_id']}: {str(e)}")
        
        return success_indices
    
    def post(self, shared, prep_res, exec_res):
        """更新推送状态"""
        success_indices = exec_res
        
        if not success_indices:
            logging.info("没有成功推送的论文")
            return "default"
        
        # 更新推送状态
        df = shared.get("processed_papers", pd.DataFrame())
        query_params = shared.get("query_params", {})
        meta_file = query_params.get("meta_file", "")
        
        df = update_push_status(df, success_indices, meta_file)
        shared["processed_papers"] = df
        shared["push_results"] = success_indices
        
        logging.info(f"成功推送{len(success_indices)}篇论文")
        return "default"

class GenerateDailyReportNode(Node):
    """生成日报节点"""
    
    def prep(self, shared):
        """获取今日论文数据"""
        df = shared.get("processed_papers", pd.DataFrame())
        lm = shared.get("lm")
        
        if df.empty:
            return None, None
        
        # 获取今日论文
        target_date = datetime.date.today()
        daily_papers = get_daily_papers_from_df(df, target_date)
        
        if daily_papers.empty:
            logging.info(f"{target_date} 没有论文需要生成日报")
            return None, None
        
        # 构建汇总文本
        combined_text = "今日论文汇总：\n\n"
        for counter, (idx, row) in enumerate(daily_papers.iterrows(), 1):
            combined_text += f"【论文{counter}】{row['paper_title']}\nAI总结：{row['summary']}...\n\n"
        
        return combined_text, lm
    
    def exec(self, prep_res):
        """生成日报"""
        combined_text, lm = prep_res
        
        if not combined_text or not lm:
            return None
        
        # 生成日报
        daily_report = generate_daily_summary(lm, combined_text)
        logging.info("日报生成完成")
        
        return daily_report
    
    def post(self, shared, prep_res, exec_res):
        """推送日报"""
        daily_report = exec_res
        
        if not daily_report:
            logging.info("没有日报需要推送")
            return "default"
        
        # 推送日报
        target_date = datetime.date.today()
        success = send_daily_report_to_feishu(daily_report, str(target_date))
        
        shared["daily_report"] = daily_report
        shared["daily_report_sent"] = success
        
        if success:
            logging.info("日报推送成功")
        else:
            logging.error("日报推送失败")
        
        return "default"

# 导出所有Node类
__all__ = [
    "FetchPapersNode",
    "FilterExistingPapersNode", 
    "SavePapersNode",
    "ProcessPapersBatchNode",
    "PushToFeishuNode",
    "GenerateDailyReportNode"
] 