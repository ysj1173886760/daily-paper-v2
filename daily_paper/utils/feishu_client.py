"""
Feishu Client Utilities

封装飞书消息推送功能
"""

import requests
from daily_paper.utils.logger import logger
import os
from typing import Dict, Any
from tenacity import retry, wait_exponential, stop_after_attempt
from .arxiv_client import ArxivPaper

FEISHU_WEBHOOK_URL = None


def init_feishu(feishu_webhook_url: str):
    global FEISHU_WEBHOOK_URL
    FEISHU_WEBHOOK_URL = feishu_webhook_url


@retry(stop=stop_after_attempt(100), wait=wait_exponential(multiplier=1, min=1, max=10))
def send_to_feishu_with_retry(message: Dict[str, Any]) -> None:
    """
    带重试机制的飞书消息推送

    Args:
        message: 飞书消息体

    Raises:
        Exception: 推送失败时抛出异常
    """
    if not FEISHU_WEBHOOK_URL:
        raise ValueError("飞书Webhook地址未配置")

    response = requests.post(FEISHU_WEBHOOK_URL, json=message, timeout=10)
    response.raise_for_status()


def send_paper_to_feishu(paper: ArxivPaper, summary: str) -> bool:
    """
    发送单篇论文到飞书

    Args:
        paper: 论文信息
        summary: 论文摘要

    Returns:
        是否发送成功
    """
    if not FEISHU_WEBHOOK_URL:
        logger.error("飞书Webhook地址未配置")
        return False

    formatted_summary = summary.replace("\\n", "\n")

    message = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**{paper.paper_title}**\n"
                        f"**更新时间**: {paper.update_time}\n\n"
                        f"👤 {paper.paper_authors}\n\n"
                        f"💡 {formatted_summary}\n\n"
                        f"---\n"
                        f"📎 [论文原文]({paper.paper_url})",
                        "tag": "lark_md",
                    },
                }
            ],
            "header": {"title": {"content": "📄 新论文推荐", "tag": "plain_text"}},
        },
    }

    try:
        send_to_feishu_with_retry(message)
        logger.info(f"飞书推送成功: {paper.paper_id}")
        return True
    except Exception as e:
        logger.error(f"飞书推送失败: {str(e)}")
        return False


def send_daily_report_to_feishu(report_content: str, target_date: str) -> bool:
    """
    发送日报到飞书

    Args:
        report_content: 日报内容
        target_date: 目标日期

    Returns:
        是否发送成功
    """
    if not FEISHU_WEBHOOK_URL:
        logger.error("飞书Webhook地址未配置")
        return False

    message = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"📅 AI论文简报({target_date})\n\n{report_content}",
                        "tag": "lark_md",
                    },
                }
            ],
            "header": {
                "title": {"content": f"{target_date} 论文日报", "tag": "plain_text"}
            },
        },
    }

    try:
        send_to_feishu_with_retry(message)
        logger.info(f"飞书日报推送成功: {target_date}")
        return True
    except Exception as e:
        logger.error(f"飞书日报推送失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 测试函数
    test_paper = ArxivPaper(
        paper_id="test123",
        paper_title="Test Paper",
        paper_url="https://arxiv.org/abs/test123",
        paper_abstract="This is a test paper",
        paper_authors="Test Author",
        paper_first_author="Test Author",
        primary_category="cs.AI",
        publish_time="2024-01-01",
        update_time="2024-01-01",
        comments=None,
    )

    test_summary = "这是一篇测试论文的摘要"

    if FEISHU_WEBHOOK_URL:
        result = send_paper_to_feishu(test_paper, test_summary)
        print(f"测试推送结果: {result}")
    else:
        print("请设置FEISHU_WEBHOOK_URL环境变量")
