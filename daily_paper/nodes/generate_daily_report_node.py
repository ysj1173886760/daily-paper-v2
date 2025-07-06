"""
GenerateDailyReportNode - 生成日报节点
"""

import datetime
import pandas as pd
from pocketflow import Node
from daily_paper.utils.feishu_client import send_daily_report_to_feishu
from daily_paper.utils.call_llm import call_llm
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager


def generate_daily_summary(combined_text):
    """
    生成日报摘要

    Args:
        lm: dspy LM对象
        combined_text: 组合的论文文本

    Returns:
        日报摘要
    """
    prompt = (
        f"请将以下论文汇总信息整理成一份结构清晰的每日简报（使用中文）：\n{combined_text}\n"
        "要求：\n1. 分领域总结研究趋势\n2. 用简洁的bullet points呈现\n3. 推荐3篇最值得阅读的论文并说明理由\n4. 领域相关趋势列出相关论文标题\n5. 论文标题用英文表达\n"
        "6.只输出分领域研究趋势总结和推荐阅读论文，不需要输出其他内容\n7.论文标题输出时不要省略"
    )
    return call_llm(prompt)


class GenerateDailyReportNode(Node):
    """生成日报节点"""

    def prep(self, shared):
        """获取今日论文数据"""
        lm = shared.get("lm")
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取今日论文
        target_date = datetime.date.today()
        daily_papers = paper_manager.get_paper_by_day(target_date)

        if daily_papers.empty:
            logger.info(f"{target_date} 没有论文需要生成日报")
            return None, None

        # 构建汇总文本
        combined_text = "今日论文汇总：\n\n"
        for counter, (idx, row) in enumerate(daily_papers.iterrows(), 1):
            combined_text += (
                f"【论文{counter}】{row['paper_title']}\nAI总结：{row['summary']}...\n\n"
            )

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
