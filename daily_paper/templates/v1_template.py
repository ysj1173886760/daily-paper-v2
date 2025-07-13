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
请仔细阅读以下论文内容，并回答下列问题，用中文回答：

论文内容：
{paper_text}

请按照以下格式回答，每个问题用一个单独的字段表示：

```yaml
problem: |
  论文要解决的是什么样的问题
background: |
  前人是怎么研究这个问题的，现在水平如何
idea_source: |
  这篇论文的idea从哪里来
solution: |
  论文的具体方案是什么
experiment: |
  论文是怎么设计实验来验证方案效果的
conclusion: |
  这篇论文能得出什么样的结论
future_work: |
  相关工作未来还有哪些思路
pseudocode: |
  用伪代码描述一下论文的核心思想
```

请确保输出格式严格按照上述YAML格式，每个字段都要填写完整。
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
                "problem": "🎯 **要解决的问题**",
                "background": "📚 **研究背景**",
                "idea_source": "💡 **创新来源**",
                "solution": "🛠️ **解决方案**",
                "experiment": "🧪 **实验设计**",
                "conclusion": "📊 **研究结论**",
                "future_work": "🔮 **未来方向**",
                "pseudocode": "💻 **核心算法**",
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
