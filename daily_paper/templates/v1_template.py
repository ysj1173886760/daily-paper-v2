"""
V1版本论文分析模板 - 经典8字段分析
"""

import yaml
from .base import PaperAnalysisTemplate


class V1Template(PaperAnalysisTemplate):
    """V1版本的论文分析模板，提供经典8字段分析"""

    @property
    def name(self) -> str:
        return "v1"

    @property
    def description(self) -> str:
        return "经典论文分析模板，包含8个核心维度的分析"

    def generate_prompt(self, paper_text: str) -> str:
        """生成V1版本的分析prompt"""
        return f"""
请仔细阅读以下论文内容，并按照结构化格式进行深度分析，用中文回答：

论文内容：
{paper_text}

请严格按照以下YAML格式输出分析结果，每个字段都要详细填写：

```yaml
# 问题定义
problem: |
  1. 论文要解决什么具体问题？
  2. 这个问题的重要性体现在哪里？
  3. 目前存在什么挑战或困难？

# 研究背景
background: |
  1. 前人在这个领域有哪些研究成果？
  2. 现有方法的优点和局限性是什么？
  3. 当前技术水平达到了什么程度？

# 创新来源
idea_source: |
  1. 这篇论文的核心思路从何而来？
  2. 灵感是否来自其他领域或技术？
  3. 作者是如何产生这个创新想法的？

# 解决方案
solution: |
  1. 论文提出的具体技术方案是什么？
  2. 关键技术细节和实现要点有哪些？

# 实验验证
experiment: |
  1. 实验是如何设计和安排的？
  2. 使用了哪些数据集、基准和评估指标？
  3. 实验结果如何，是否有效证明了方案的可行性？

# 研究结论
conclusion: |
  1. 论文得出了什么重要结论？
  2. 主要贡献和成果有哪些？
  3. 这些结论对领域发展有什么意义？

# 未来展望
future_work: |
  1. 当前工作还存在哪些局限性？
  2. 未来可能的改进方向和研究思路？
  3. 相关领域还有哪些值得深入探索的问题？

# 核心算法
pseudocode: |
  用伪代码描述论文的核心算法流程
```

请确保：
1. 严格按照上述YAML格式输出
2. 每个字段都要认真分析并填写具体内容，避免空泛回答
3. 分析要深入透彻，体现对论文的深度理解
4. 输出具有结构化，不要吝啬使用换行符，让用户可以轻松阅读，避免把文字堆砌在一起
"""

    def parse_response(self, response: str) -> str:
        """解析V1版本的响应"""
        yaml_content = self._extract_yaml_content(response)

        # 解析YAML验证格式
        analysis = yaml.safe_load(yaml_content)

        # 验证并补充缺失字段
        analysis = self._validate_fields(analysis)

        return yaml_content

    def _extract_yaml_content(self, response: str) -> str:
        """从LLM响应中提取YAML内容"""
        yaml_start = response.find("```yaml")
        yaml_end = response.find("```", yaml_start + 7)

        if yaml_start != -1 and yaml_end != -1:
            return response[yaml_start + 7 : yaml_end].strip()
        else:
            raise Exception("未找到YAML格式的回答")

    def _get_required_fields(self) -> list[str]:
        """获取V1版本的必需字段"""
        return [
            "problem",
            "background",
            "idea_source",
            "solution",
            "experiment",
            "conclusion",
            "future_work",
            "pseudocode",
        ]

    def _validate_fields(self, analysis: dict) -> dict:
        """验证所有必需字段是否存在，缺失的字段填充默认值"""
        required_fields = self._get_required_fields()

        for field in required_fields:
            if field not in analysis:
                analysis[field] = "分析不完整"

        return analysis

    def format_to_markdown(self, content: str) -> str:
        """将V1版本的YAML转换为Markdown（兼容原有格式）"""
        try:
            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                return f"```\n{content}\n```"

            # 定义字段标题映射（保持原有样式）
            field_titles = {
                "problem": "**要解决的问题**",
                "background": "**研究背景**",
                "idea_source": "**创新来源**",
                "solution": "**解决方案**",
                "experiment": "**实验设计**",
                "conclusion": "**研究结论**",
                "future_work": "**未来方向**",
                "pseudocode": "**核心算法**",
            }

            markdown_parts = []

            # 按预定义顺序处理字段
            field_order = [
                "problem",
                "background",
                "idea_source",
                "solution",
                "experiment",
                "conclusion",
                "future_work",
                "pseudocode",
            ]

            for field in field_order:
                if field in data and data[field]:
                    title = field_titles.get(field, f"**{field.upper()}**")
                    content_text = str(data[field]).strip()

                    # 特殊处理伪代码字段
                    if field == "pseudocode":
                        markdown_parts.append(f"{title}\n```\n{content_text}\n```")
                    else:
                        markdown_parts.append(f"{title}\n{content_text}")

            # 处理其他未预定义的字段
            for key, value in data.items():
                if key not in field_order and value:
                    title = f"**{key.upper()}**"
                    content_text = str(value).strip()
                    markdown_parts.append(f"{title}\n{content_text}")

            return "\n\n".join(markdown_parts)

        except yaml.YAMLError as e:
            return (
                f"❌ **YAML解析错误**\n```\n{str(e)}\n```\n\n**原始内容：**\n```\n{content}\n```"
            )
        except Exception as e:
            return f"❌ **转换错误**\n```\n{str(e)}\n```\n\n**原始内容：**\n```\n{content}\n```"
