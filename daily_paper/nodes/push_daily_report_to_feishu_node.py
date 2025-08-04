"""
Push Daily Report to Feishu Node

格式化并推送日报到飞书的节点
"""

from typing import List, Dict, Any
from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger
from daily_paper.utils.feishu_client import send_to_feishu_with_retry
from daily_paper.utils.date_helper import format_date_chinese


class PushDailyReportToFeishuNode(Node):
    """格式化并推送日报到飞书的节点"""
    
    def __init__(self):
        """初始化节点"""
        super().__init__(max_retries=2, wait=3)
    
    def prep(self, shared):
        """准备阶段：从shared获取分析结果和论文数据"""
        analysis_and_recommendations = shared.get("analysis_and_recommendations")
        yesterday_papers = shared.get("yesterday_papers", [])
        target_date = shared.get("target_date")
        
        if not analysis_and_recommendations:
            raise ValueError("analysis_and_recommendations not found in shared store")
        
        if not target_date:
            raise ValueError("target_date not found in shared store")
        
        return {
            "analysis_result": analysis_and_recommendations,
            "papers": yesterday_papers,
            "target_date": target_date
        }
    
    def exec(self, prep_res):
        """执行阶段：格式化报告并推送到飞书"""
        analysis_result = prep_res["analysis_result"]
        papers = prep_res["papers"]
        target_date = prep_res["target_date"]
        
        logger.info("开始格式化日报并推送到飞书")
        
        # 格式化报告内容
        report_content = self._format_daily_report(analysis_result, papers, target_date)
        
        # 推送到飞书
        try:
            # 构建飞书消息格式
            feishu_message = self._build_feishu_message(report_content)
            result = send_to_feishu_with_retry(feishu_message)
            logger.info("日报已成功推送到飞书")
            return {
                "success": True,
                "result": result,
                "content": report_content
            }
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
    
    def _build_feishu_message(self, report_content: str) -> Dict[str, Any]:
        """构建飞书消息格式"""
        return {
            "msg_type": "interactive",
            "card": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": report_content,
                            "tag": "lark_md",
                        },
                    }
                ],
                "header": {"title": {"content": "📊 AI论文日报", "tag": "plain_text"}},
            },
        }
    
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
                    f"### {i}. {rec['title']}",
                    f"**论文介绍**: {rec.get('description', '暂无详细介绍')}",
                    f"**推荐理由**: {rec['reason']}",
                    f"**核心亮点**: {' | '.join(rec['highlights'])}",
                ])
                
                if paper:
                    report_lines.extend([
                        f"**链接**: {paper.paper_url}",
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
            feishu_message = self._build_feishu_message(simple_report)
            result = send_to_feishu_with_retry(feishu_message)
            return {
                "success": True,
                "result": result,
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