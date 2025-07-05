"""
GenerateDailyReportNode - 生成日报节点
"""

import datetime
import pandas as pd
from pocketflow import Node
from daily_paper.utils.data_manager import get_daily_papers as get_daily_papers_from_df
from daily_paper.utils.feishu_client import send_daily_report_to_feishu
from daily_paper.utils.call_llm import generate_daily_summary
from daily_paper.utils.logger import logger

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
            logger.info(f"{target_date} 没有论文需要生成日报")
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
        logger.info("日报生成完成")
        
        return daily_report
    
    def post(self, shared, prep_res, exec_res):
        """推送日报"""
        daily_report = exec_res
        
        if not daily_report:
            logger.info("没有日报需要推送")
            return "default"
        
        # 推送日报
        target_date = datetime.date.today()
        success = send_daily_report_to_feishu(daily_report, str(target_date))
        
        shared["daily_report"] = daily_report
        shared["daily_report_sent"] = success
        
        if success:
            logger.info("日报推送成功")
        else:
            logger.error("日报推送失败")
        
        return "default" 