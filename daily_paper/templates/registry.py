"""
模板注册系统 - 管理和获取论文分析模板
"""

from typing import Dict, Type
from .base import PaperAnalysisTemplate
from .v1_template import V1Template
from .v2_template import V2Template
from .simple_template import SimpleTemplate


class TemplateRegistry:
    """模板注册表，管理所有可用的分析模板"""

    _templates: Dict[str, Type[PaperAnalysisTemplate]] = {}
    _initialized = False

    @classmethod
    def _initialize(cls):
        """初始化注册表，注册所有内置模板"""
        if cls._initialized:
            return

        cls.register("simple", SimpleTemplate)
        cls.register("v1", V1Template)
        cls.register("v2", V2Template)
        cls._initialized = True

    @classmethod
    def register(cls, name: str, template_class: Type[PaperAnalysisTemplate]):
        """注册一个模板类

        Args:
            name: 模板名称
            template_class: 模板类
        """
        cls._templates[name] = template_class

    @classmethod
    def get_template(cls, name: str) -> PaperAnalysisTemplate:
        """获取指定名称的模板实例

        Args:
            name: 模板名称

        Returns:
            PaperAnalysisTemplate: 模板实例

        Raises:
            ValueError: 当模板不存在时
        """
        cls._initialize()

        if name not in cls._templates:
            available_templates = list(cls._templates.keys())
            raise ValueError(f"未找到模板 '{name}'。可用模板: {available_templates}")

        template_class = cls._templates[name]
        return template_class()

    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """列出所有可用模板及其描述

        Returns:
            Dict[str, str]: 模板名称到描述的映射
        """
        cls._initialize()

        result = {}
        for name, template_class in cls._templates.items():
            template_instance = template_class()
            result[name] = template_instance.description

        return result

    @classmethod
    def exists(cls, name: str) -> bool:
        """检查指定名称的模板是否存在

        Args:
            name: 模板名称

        Returns:
            bool: 模板是否存在
        """
        cls._initialize()
        return name in cls._templates


def get_template(name: str) -> PaperAnalysisTemplate:
    """获取指定名称的模板实例（便捷函数）

    Args:
        name: 模板名称

    Returns:
        PaperAnalysisTemplate: 模板实例

    Raises:
        ValueError: 当模板不存在时
    """
    return TemplateRegistry.get_template(name)


def list_templates() -> Dict[str, str]:
    """列出所有可用模板及其描述（便捷函数）

    Returns:
        Dict[str, str]: 模板名称到描述的映射
    """
    return TemplateRegistry.list_templates()


if __name__ == "__main__":
    # 测试代码
    print("=== 可用模板 ===")
    templates = list_templates()
    for name, description in templates.items():
        print(f"{name}: {description}")

    print("\n=== 测试V1模板 ===")
    v1_template = get_template("v1")
    print(f"名称: {v1_template.name}")
    print(f"描述: {v1_template.description}")
    print(f"必需字段: {v1_template.get_required_fields()}")

    print("\n=== 测试V2模板 ===")
    v2_template = get_template("v2")
    print(f"名称: {v2_template.name}")
    print(f"描述: {v2_template.description}")
    print(f"必需字段: {v2_template.get_required_fields()}")
