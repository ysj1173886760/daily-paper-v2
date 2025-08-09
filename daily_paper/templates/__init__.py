"""
论文分析模板系统
"""

from .base import PaperAnalysisTemplate
from .registry import TemplateRegistry, get_template, list_templates
from .v1_template import V1Template
from .v2_template import V2Template
from .simple_template import SimpleTemplate
from .analysis_template import FastAnalysisTemplate

__all__ = [
    "PaperAnalysisTemplate",
    "TemplateRegistry",
    "get_template",
    "list_templates",
    "V1Template",
    "V2Template",
    "SimpleTemplate",
    "FastAnalysisTemplate",
]
