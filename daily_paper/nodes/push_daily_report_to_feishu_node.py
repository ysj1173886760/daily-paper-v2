"""
Push Daily Report to Feishu Node

格式化并推送日报到飞书的节点
"""

from typing import List, Dict, Any
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger
from daily_paper.utils.feishu_client import FeishuClient
from daily_paper.utils.date_helper import format_date_chinese


class PushDailyReportToFeishuNode(Node):
    """格式化并推送日报到飞书的节点"""
    
    def __init__(self, feishu_client: FeishuClient = None):
        """
        初始化节点
        
        Args:
            feishu_client: 飞书客户端，如果不提供则从配置中创建
        """
        super().__init__(max_retries=2, wait=3)
        self.feishu_client = feishu_client
    
    def prep(self, shared):
        """准备阶段：从shared获取分析结果和论文数据"""
        analysis_and_recommendations = shared.get("analysis_and_recommendations")
        yesterday_papers = shared.get("yesterday_papers", [])
        target_date = shared.get("target_date")
        config = shared.get("config")
        
        if not analysis_and_recommendations:
            raise ValueError("analysis_and_recommendations not found in shared store")
        
        if not target_date:
            raise ValueError("target_date not found in shared store")
        
        # 获取飞书客户端
        feishu_client = self.feishu_client
        if not feishu_client and config:
            # 优先使用每日汇总专用的webhook URL
            webhook_url = None
            if hasattr(config, 'daily_summary_feishu_webhook_url') and config.daily_summary_feishu_webhook_url:
                webhook_url = config.daily_summary_feishu_webhook_url
                logger.info("使用每日汇总专用的飞书webhook URL")
            elif hasattr(config, 'feishu_webhook_url') and config.feishu_webhook_url:
                webhook_url = config.feishu_webhook_url
                logger.info("使用默认的飞书webhook URL")
            
            if webhook_url:
                feishu_client = FeishuClient(webhook_url)
        
        if not feishu_client:
            raise ValueError("飞书客户端未配置，请传入 feishu_client 或在 config 中设置 feishu_webhook_url")
        
        return {
            "analysis_result": analysis_and_recommendations,
            "papers": yesterday_papers,
            "target_date": target_date,
            "feishu_client": feishu_client
        }
    
    def exec(self, prep_res):
        """执行阶段：格式化报告并推送到飞书"""
        analysis_result = prep_res["analysis_result"]
        papers = prep_res["papers"]
        target_date = prep_res["target_date"]
        feishu_client = prep_res["feishu_client"]
        
        logger.info("开始格式化日报并推送到飞书")
        
        # 格式化报告内容
        report_content = self._format_daily_report(analysis_result, papers, target_date)
        
        # 推送到飞书
        try:
            success = feishu_client.send_daily_report(report_content)
            if success:
                logger.info("日报已成功推送到飞书")
                return {
                    "success": True,
                    "content": report_content
                }
            else:
                raise Exception("飞书客户端返回推送失败")
        except Exception as e:
            logger.error(f"推送到飞书失败: {str(e)}")
            raise
    
    def post(self, shared, prep_res, exec_res):
        """后处理阶段：将推送结果存储到shared"""
        shared["push_result"] = exec_res
        
        if exec_res["success"]:
            logger.info("日报推送完成")
        else:
            logger.error("日报推送失败")
        
        return "default"
    
    
    def _format_daily_report(self, analysis_result: Dict[str, Any], papers: List[ArxivPaper], target_date) -> str:
        """格式化日报内容"""
        date_str = format_date_chinese(target_date)
        summary_stats = analysis_result.get("summary_stats", {})
        recommendations = analysis_result.get("recommendations", [])
        
        # 构建报告内容
        report_lines = [
            f"# 📊 AI论文日报 - {date_str}",
            "",
            "## 📈 今日概览",
            f"- **论文总数**: {summary_stats.get('total_papers', len(papers))}篇",
            f"- **推荐论文**: {len(recommendations)}篇",
            f"- **主要领域**: {', '.join(summary_stats.get('main_categories', []))}",
            f"- **热点话题**: {', '.join(summary_stats.get('key_topics', []))}",
            ""
        ]
        
        # 添加推荐论文
        if recommendations:
            report_lines.extend([
                "## ⭐ 推荐论文",
                ""
            ])
            
            for i, rec in enumerate(recommendations, 1):
                # 从papers中找到对应的论文获取更多信息
                paper = self._find_paper_by_id(papers, rec["paper_id"])
                
                report_lines.extend([
                    f"### {i}. **{rec['title']}**",
                    f"**论文介绍**: {rec.get('description', '暂无详细介绍')}",
                    f"**推荐理由**: {rec['reason']}",
                    f"**核心亮点**: {' | '.join(rec['highlights'])}",
                ])
                
                if paper:
                    report_lines.extend([
                        f"**作者**: {paper.paper_first_author}",
                        f"**分类**: {paper.primary_category}",
                        f"**链接**: [{paper.paper_id}]({paper.paper_url})",
                    ])
                    
                report_lines.append("")
        
        
        # 添加footer
        report_lines.extend([
            "---",
            f"*📅 报告生成时间: {date_str}*",
            "*🤖 由AI论文助手自动生成*"
        ])
        
        return "\n".join(report_lines)
    
    def _find_paper_by_id(self, papers: List[ArxivPaper], paper_id: str) -> ArxivPaper:
        """根据paper_id查找论文"""
        for paper in papers:
            if paper.paper_id == paper_id:
                return paper
        return None
    
    def exec_fallback(self, prep_res, exc):
        """失败回退：返回基础报告"""
        target_date = prep_res["target_date"]
        papers = prep_res["papers"]
        
        logger.warning(f"推送失败，使用回退方案: {exc}")
        
        # 生成简化的报告内容
        simple_report = f"""# 📊 AI论文日报 - {format_date_chinese(target_date)}

## 概览
今日共收录 {len(papers)} 篇论文。

由于服务暂时不可用，无法提供详细分析。请查看完整论文列表：

"""
        
        for i, paper in enumerate(papers, 1):
            simple_report += f"{i}. {paper.paper_title}\n"
            simple_report += f"   - 作者: {paper.paper_first_author}\n"
            simple_report += f"   - 链接: {paper.paper_url}\n\n"
        
        try:
            # 使用准备阶段创建的飞书客户端
            feishu_client = prep_res["feishu_client"]
            success = feishu_client.send_daily_report(simple_report, "📊 AI论文日报（简化版）")
            return {
                "success": success,
                "content": simple_report,
                "fallback": True
            }
        except Exception as fallback_exc:
            logger.error(f"回退方案也失败了: {fallback_exc}")
            return {
                "success": False,
                "error": str(fallback_exc),
                "content": simple_report,
                "fallback": True
            }