"""
Simple版本论文分析模板 - 简单摘要生成
"""

from .base import PaperAnalysisTemplate


class SimpleTemplate(PaperAnalysisTemplate):
    """Simple版本的论文分析模板，提供简单的文章介绍"""

    @property
    def name(self) -> str:
        return "simple"

    @property
    def description(self) -> str:
        return "简单摘要模板，生成基础的论文介绍"

    def generate_prompt(self, paper_text: str) -> str:
        """生成Simple版本的分析prompt"""
        return f"用中文帮我介绍一下这篇文章: {paper_text}"

    def parse_response(self, response: str) -> str:
        """解析Simple版本的响应 - 直接返回原始文本"""
        # Simple模板直接返回LLM的响应，不需要特殊解析
        return response.strip()

    def format_to_markdown(self, content: str) -> str:
        """将Simple版本的内容转换为Markdown - 直接输出"""
        # Simple模板的内容已经是纯文本，直接返回即可
        return content
