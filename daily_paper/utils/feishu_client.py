"""
Feishu Client Utilities

封装飞书消息推送功能
"""

import requests
from daily_paper.utils.logger import logger
from typing import Dict, Any, Optional
from tenacity import retry, wait_exponential, stop_after_attempt
from daily_paper.model.arxiv_paper import ArxivPaper


def create_feishu_client(webhook_url: str) -> 'FeishuClient':
    """
    创建飞书客户端的工厂函数
    
    Args:
        webhook_url: 飞书机器人的 Webhook URL
        
    Returns:
        FeishuClient 实例
    """
    return FeishuClient(webhook_url)


class FeishuClient:
    """飞书客户端"""
    
    def __init__(self, webhook_url: str):
        """
        初始化飞书客户端
        
        Args:
            webhook_url: 飞书机器人的 Webhook URL
        """
        if not webhook_url:
            raise ValueError("Webhook URL cannot be empty")
        
        self.webhook_url = webhook_url
        logger.debug(f"初始化飞书客户端: {webhook_url}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        带重试机制的飞书消息推送
        
        Args:
            message: 飞书消息体
            
        Returns:
            API 响应结果
            
        Raises:
            Exception: 推送失败时抛出异常
        """
        response = requests.post(self.webhook_url, json=message, timeout=10)
        
        try:
            response.raise_for_status()
            result = response.json()
            
            # 检查飞书API返回的状态
            if result.get("code") != 0:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"飞书API返回错误: {error_msg}")
                raise ValueError(f"飞书API错误: {error_msg}")
            
            return result
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP请求失败: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求异常: {str(e)}")
            raise
    
    def send_paper(self, paper: ArxivPaper, summary: str) -> bool:
        """
        发送单篇论文到飞书
        
        Args:
            paper: 论文信息
            summary: 论文摘要
            
        Returns:
            是否发送成功
        """
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
            result = self.send_message(message)
            logger.info(f"飞书推送成功: {paper.paper_id}")
            return True
        except Exception as e:
            logger.error(f"飞书推送失败 {paper.paper_id}: {str(e)}")
            return False
    
    def send_daily_report(self, content: str, title: str = "📊 AI论文日报") -> bool:
        """
        发送每日报告到飞书
        
        Args:
            content: 报告内容（Markdown格式）
            title: 报告标题
            
        Returns:
            是否发送成功
        """
        message = {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": content,
                            "tag": "lark_md",
                        },
                    }
                ],
                "header": {"title": {"content": title, "tag": "plain_text"}},
            },
        }
        
        try:
            result = self.send_message(message)
            logger.info("每日报告推送成功")
            return True
        except Exception as e:
            logger.error(f"每日报告推送失败: {str(e)}")
            return False
    
    def send_text(self, text: str) -> bool:
        """
        发送纯文本消息到飞书
        
        Args:
            text: 文本内容
            
        Returns:
            是否发送成功
        """
        message = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        try:
            result = self.send_message(message)
            logger.info("文本消息推送成功")
            return True
        except Exception as e:
            logger.error(f"文本消息推送失败: {str(e)}")
            return False



if __name__ == "__main__":
    # 测试函数
    import os
    
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("请设置 FEISHU_WEBHOOK_URL 环境变量")
        exit(1)
    
    # 创建飞书客户端
    client = FeishuClient(webhook_url)
    
    # 测试发送文本消息
    success = client.send_text("这是一条测试消息 🚀")
    print(f"文本消息测试结果: {success}")
    
    # 测试发送论文
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
    
    test_summary = "这是一篇测试论文的摘要，展示了飞书客户端的功能"
    success = client.send_paper(test_paper, test_summary)
    print(f"论文推送测试结果: {success}")
    
    # 测试发送日报
    test_report = """# 📊 AI论文日报 - 2025年8月9日

## 📈 今日概览
- **论文总数**: 5篇
- **推荐论文**: 3篇
- **主要领域**: RAG, Knowledge Graph

## ⭐ 推荐论文

### 1. 测试论文标题
**论文介绍**: 这是一个测试的论文介绍，展示日报格式
**推荐理由**: 技术创新有价值
**核心亮点**: 新方法 | 性能提升 | 实用性强

---
*📅 报告生成时间: 2025年8月9日*
*🤖 由AI论文助手自动生成*"""
    
    success = client.send_daily_report(test_report)
    print(f"日报推送测试结果: {success}")
