"""
Analyze and Recommend Papers Node

分析并推荐论文的节点
"""

import json
from typing import Any, Dict, List

from pocketflow import Node

from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.call_llm import LLM
from daily_paper.utils.date_helper import format_date_chinese
from daily_paper.utils.llm_manager import LLMManager
from daily_paper.utils.logger import logger


class AnalyzeAndRecommendPapersNode(Node):
    """分析并推荐论文的节点"""

    def __init__(
        self,
        recommendation_count: int = 3,
        *,
        llm_profile: str = "analysis",
    ):
        """
        初始化节点

        Args:
            recommendation_count: 推荐论文数量，默认3篇
        """
        super().__init__(max_retries=2, wait=5)
        self.recommendation_count = recommendation_count
        self.llm_profile = llm_profile

    def prep(self, shared):
        """准备阶段：从shared获取昨日论文"""
        yesterday_papers = shared.get("yesterday_papers", [])
        target_date = shared.get("target_date")
        config = shared.get("config")
        llm_manager: LLMManager | None = shared.get("llm_manager")
        if llm_manager is not None:
            llm = llm_manager.get_llm(self.llm_profile)
        else:
            llm = shared.get("llm")

        if llm is None:
            raise RuntimeError(
                "LLM instance not found in shared store. Please set shared['llm'] or shared['llm_manager'] before running."
            )

        if not yesterday_papers:
            raise ValueError("yesterday_papers not found in shared store")

        if not target_date:
            raise ValueError("target_date not found in shared store")

        # 使用配置文件中的推荐数量，如果配置存在的话
        recommendation_count = self.recommendation_count
        if config and hasattr(config, "daily_summary_recommendation_count"):
            recommendation_count = config.daily_summary_recommendation_count

        return {
            "papers": yesterday_papers,
            "target_date": target_date,
            "recommendation_count": recommendation_count,
            "llm": llm,
        }

    def exec(self, prep_res):
        """执行阶段：调用LLM进行分析和推荐"""
        papers = prep_res["papers"]
        target_date = prep_res["target_date"]
        recommendation_count = prep_res["recommendation_count"]
        llm: LLM = prep_res["llm"]

        logger.info(f"开始分析 {len(papers)} 篇论文并生成推荐")

        # 构建论文信息列表
        papers_info = []
        for i, paper in enumerate(papers, 1):
            paper_info = {
                "序号": i,
                "paper_id": paper.paper_id,
                "标题": paper.paper_title,
                "作者": paper.paper_first_author,
                "分类": paper.primary_category,
                "摘要分析": paper.summary,
            }
            papers_info.append(paper_info)

        # 构建prompt
        prompt = self._build_analysis_prompt(
            papers_info, target_date, recommendation_count
        )

        # 调用LLM
        try:
            response = llm.chat(prompt)
            logger.debug(f"LLM原始响应: {response}")

            # 解析LLM响应
            result = self._parse_llm_response(response)

            logger.info("论文分析和推荐完成")
            return result

        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise

    def post(self, shared, prep_res, exec_res):
        """后处理阶段：将结果存储到shared"""
        shared["analysis_and_recommendations"] = exec_res

        num_recommendations = len(exec_res.get("recommendations", []))
        logger.info(f"已生成分析报告和 {num_recommendations} 个推荐")

        return "default"

    def _build_analysis_prompt(
        self, papers_info: List[Dict], target_date, recommendation_count: int
    ) -> str:
        """构建分析prompt"""
        papers_json = json.dumps(papers_info, ensure_ascii=False, indent=2)
        date_str = format_date_chinese(target_date)

        prompt = f"""你是一个AI论文分析专家。请分析以下{date_str}的论文，并推荐最有价值的论文。

论文信息：
{papers_json}

请按照以下JSON格式输出推荐结果：

```json
{{
  "summary_stats": {{
    "total_papers": {len(papers_info)},
    "main_categories": ["主要研究分类1", "主要研究分类2"],
    "key_topics": ["热点话题1", "热点话题2", "热点话题3"]
  }},
  "recommendations": [
    {{
      "paper_id": "推荐论文1的paper_id",
      "title": "推荐论文1的标题",
      "description": "详细描述这篇论文的研究内容、方法、创新点和贡献，包括解决了什么问题、采用了什么技术方案、取得了什么成果等，100-150字",
      "reason": "推荐理由，说明为什么这篇论文值得关注，包括学术价值、实用性、影响力等，60-80字",
      "highlights": ["技术亮点1", "创新亮点2", "应用亮点3"]
    }},
    {{
      "paper_id": "推荐论文2的paper_id", 
      "title": "推荐论文2的标题",
      "description": "详细描述论文内容，100-150字",
      "reason": "推荐理由，60-80字",
      "highlights": ["技术亮点1", "创新亮点2", "应用亮点3"]
    }},
    {{
      "paper_id": "推荐论文3的paper_id",
      "title": "推荐论文3的标题", 
      "description": "详细描述论文内容，100-150字",
      "reason": "推荐理由，60-80字",
      "highlights": ["技术亮点1", "创新亮点2", "应用亮点3"]
    }}
  ]
}}
```

要求：
1. 请推荐最具价值的{recommendation_count}篇论文
2. description要详细介绍论文的研究内容、技术方案和贡献
3. reason要客观具体地说明推荐价值
4. highlights要准确概括技术创新和应用价值
5. 严格按照JSON格式输出，确保格式正确"""

        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 提取JSON内容
            json_start = response.find("```json")
            json_end = response.find("```", json_start + 7)

            if json_start != -1 and json_end != -1:
                json_content = response[json_start + 7 : json_end].strip()
            else:
                # 尝试直接解析整个响应
                json_content = response.strip()

            # 解析JSON
            result = json.loads(json_content)

            # 验证必需字段
            required_fields = ["summary_stats", "recommendations"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"LLM响应缺少必需字段: {field}")

            # 验证推荐列表
            recommendations = result["recommendations"]
            if not isinstance(recommendations, list) or len(recommendations) == 0:
                raise ValueError("推荐列表为空或格式错误")

            # 验证每个推荐的必需字段
            for i, rec in enumerate(recommendations):
                rec_fields = [
                    "paper_id",
                    "title",
                    "description",
                    "reason",
                    "highlights",
                ]
                for field in rec_fields:
                    if field not in rec:
                        raise ValueError(f"推荐{i+1}缺少字段: {field}")

            logger.info(f"成功解析LLM响应，包含{len(recommendations)}个推荐")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response}")
            raise ValueError(f"LLM返回的JSON格式不正确: {e}")
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            raise

    def exec_fallback(self, prep_res, exc):
        """失败回退：返回基础分析结果"""
        papers = prep_res["papers"]
        target_date = prep_res["target_date"]

        logger.warning(f"LLM分析失败，使用回退方案: {exc}")

        # 生成基础统计信息
        categories = list(set(paper.primary_category for paper in papers))

        # 简单推荐：选择前几篇论文
        recommendations = []
        for i, paper in enumerate(papers[: self.recommendation_count]):
            recommendations.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.paper_title,
                    "description": f"该论文属于{paper.primary_category}领域，由于分析服务暂时不可用，无法提供详细内容分析。",
                    "reason": "基于时间顺序的推荐，该论文在当日发布，值得关注",
                    "highlights": ["新发布论文", "领域相关", "值得关注"],
                }
            )

        return {
            "summary_stats": {
                "total_papers": len(papers),
                "main_categories": categories[:3],  # 最多显示3个分类
                "key_topics": ["论文分析", "研究进展", "学术动态"],
            },
            "recommendations": recommendations,
        }
