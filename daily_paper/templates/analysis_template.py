"""
Fast Analysis论文分析模板 - 3个核心问题快速分析
"""

import yaml
import re
from typing import Dict, Any
from .base import PaperAnalysisTemplate


class FastAnalysisTemplate(PaperAnalysisTemplate):
    """快速论文分析模板，回答3个核心研究问题"""

    @property
    def name(self) -> str:
        return "fast_analysis"

    @property
    def description(self) -> str:
        return "快速论文分析模板，回答3个核心研究问题"

    def generate_prompt(self, paper_text: str) -> str:
        """生成结构化分析prompt"""
        return f"""
请仔细阅读以下论文内容，并按照结构化格式回答3个核心问题，用中文回答：

论文内容：
{paper_text}

请严格按照以下YAML格式输出分析结果，简洁明了地回答每个问题：

```yaml
# 1. 要解决的问题
problem: |
  [简洁描述论文要解决的核心问题及其重要性]

# 2. 方法介绍
method: |
  [详细描述论文提出的具体技术方案、核心算法或模型架构，包括关键创新点和技术细节]

# 3. 实验设计与结论
experiment_conclusion: |
  [概括实验设计、主要结果和得出的结论]
```

"""

    def parse_response(self, response: str) -> str:
        """解析LLM响应并验证结构"""
        # 提取YAML内容
        yaml_match = re.search(r'```yaml\s*\n(.*?)\n```', response, re.DOTALL)
        if not yaml_match:
            raise Exception("未找到有效的YAML格式内容")
        
        yaml_content = yaml_match.group(1)
        
        try:
            # 解析YAML
            parsed_data = yaml.safe_load(yaml_content)
            
            # 验证必需字段
            required_fields = [
                'problem', 'method', 'experiment_conclusion'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in parsed_data or not parsed_data[field] or not parsed_data[field].strip():
                    missing_fields.append(field)
            
            if missing_fields:
                raise Exception(f"缺少必需字段: {', '.join(missing_fields)}")
            
            return yaml_content
            
        except yaml.YAMLError as e:
            raise Exception(f"YAML解析错误: {e}")

    def format_to_markdown(self, content: str) -> str:
        """将结构化内容转换为Markdown格式"""
        try:
            parsed_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise Exception(f"YAML解析错误: {e}")
        
        # 字段标题映射，采用更清晰的格式
        field_titles = {
            'problem': '**🎯 要解决的问题**',
            'method': '**🔧 方法介绍**',
            'experiment_conclusion': '**📊 实验设计与结论**'
        }
        
        # 按顺序输出各个字段
        field_order = ['problem', 'method', 'experiment_conclusion']
        
        markdown_parts = []
        
        for field in field_order:
            if field in parsed_data and parsed_data[field]:
                title = field_titles.get(field, f"**{field.upper()}**")
                content_text = str(parsed_data[field]).strip()
                
                # 使用更清晰的格式，参考v1模板的布局
                markdown_parts.append(f"{title}\n{content_text}")
        
        # 组合所有部分，使用适当的空行间距
        result = "\n\n".join(markdown_parts)
        
        # 添加底部标识
        result += "\n\n---\n*📊 结构化论文分析*"
        
        return result

    def get_required_fields(self) -> list:
        """获取模板的必需字段列表"""
        return [
            'problem', 'method', 'experiment_conclusion'
        ]

    def get_field_descriptions(self) -> Dict[str, str]:
        """获取各字段的描述信息"""
        return {
            'problem': '论文要解决的核心问题及其重要性',
            'method': '论文提出的具体技术方案、核心算法或模型架构，包括关键创新点和技术细节',
            'experiment_conclusion': '实验设计、主要结果和得出的结论'
        }