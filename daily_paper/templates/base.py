"""
论文分析模板基类
"""

from abc import ABC, abstractmethod


class PaperAnalysisTemplate(ABC):
    """论文分析模板基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """模板名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """模板描述"""
        pass

    @abstractmethod
    def generate_prompt(self, paper_text: str) -> str:
        """生成分析论文的LLM prompt

        Args:
            paper_text: 论文文本内容

        Returns:
            str: 生成的prompt
        """
        pass

    @abstractmethod
    def parse_response(self, response: str) -> str:
        """解析LLM响应，提取结构化内容并验证

        Args:
            response: LLM的响应文本

        Returns:
            str: 验证后的结构化内容

        Raises:
            Exception: 当解析失败或验证失败时
        """
        pass

    @abstractmethod
    def format_to_markdown(self, content: str) -> str:
        """将结构化内容转换为Markdown格式

        Args:
            content: 结构化的分析内容

        Returns:
            str: Markdown格式的输出
        """
        pass
