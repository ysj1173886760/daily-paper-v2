"""
V2版本论文分析模板 - 深度结构化分析
"""

import yaml
from .base import PaperAnalysisTemplate


class V2Template(PaperAnalysisTemplate):
    """V2版本的论文分析模板，提供深度结构化分析"""
    
    @property
    def name(self) -> str:
        return "v2"
    
    @property 
    def description(self) -> str:
        return "深度结构化论文分析模板，包含11个维度的详细分析"
    
    def generate_prompt(self, paper_text: str) -> str:
        """生成V2版本的分析prompt"""
        return f"""
请仔细阅读以下论文内容，并按照结构化格式进行深度分析，用中文回答：

论文内容：
{paper_text}

请严格按照以下YAML格式输出分析结果，每个字段都要详细填写：

```yaml
# 论文核心信息
title: |
  论文标题（如果文中有提及）

# 问题定义与动机
problem: |
  1. 具体要解决什么问题？
  2. 这个问题为什么重要？
  3. 当前存在什么挑战或局限性？

# 研究背景与相关工作
background: |
  1. 前人在这个领域做了哪些研究？
  2. 现有方法的优缺点是什么？
  3. 目前技术水平达到了什么程度？

# 创新点与思路来源
innovation: |
  1. 这篇论文的主要创新点是什么？
  2. 灵感或思路从何而来？
  3. 与现有方法相比有什么独特之处？

# 技术方案与方法
solution: |
  1. 论文提出的具体技术方案是什么？
  2. 核心算法或模型架构如何？
  3. 关键技术细节有哪些？

# 实验设计与验证
experiment: |
  1. 实验是如何设计的？
  2. 使用了哪些数据集和评估指标？
  3. 实验结果如何，是否支持论文观点？

# 结论与贡献
conclusion: |
  1. 论文得出了什么结论？
  2. 主要贡献有哪些？
  3. 在领域内的意义是什么？

# 局限性与未来工作
future_work: |
  1. 论文存在哪些局限性？
  2. 未来可能的改进方向？
  3. 相关领域还有哪些值得探索的问题？

# 技术实现
implementation: |
  1. 核心算法的伪代码或流程描述
  2. 关键技术组件说明
  3. 实现时需要注意的要点

# 影响与应用
impact: |
  1. 这项工作可能产生什么影响？
  2. 有哪些潜在的应用场景？
  3. 对相关领域发展有什么推动作用？

# 评价与思考
evaluation: |
  1. 论文的整体质量如何？
  2. 技术路线是否合理？
  3. 还有哪些可以深入思考的角度？
```

请确保：
1. 严格按照上述YAML格式输出
2. 每个字段都要认真分析并填写具体内容，避免空泛回答
3. 分析要深入透彻，体现对论文的深度理解
4. 保持客观性，既要指出优点也要指出不足
"""
    
    def parse_response(self, response: str) -> str:
        """解析V2版本的响应"""
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
        """获取V2版本的必需字段"""
        return [
            "title",
            "problem", 
            "background",
            "innovation",
            "solution",
            "experiment", 
            "conclusion",
            "future_work",
            "implementation",
            "impact",
            "evaluation",
        ]
    
    def _validate_fields(self, analysis: dict) -> dict:
        """验证所有必需字段是否存在，缺失的字段填充默认值"""
        required_fields = self._get_required_fields()
        
        for field in required_fields:
            if field not in analysis:
                analysis[field] = "分析不完整"
                
        return analysis
    
    def format_to_markdown(self, content: str) -> str:
        """将V2版本的YAML转换为Markdown"""
        try:
            data = yaml.safe_load(content)
            
            markdown = f"""# 论文分析报告

## 📄 论文信息
**标题**: {data.get('title', '未提供').strip()}

## 🎯 问题定义与动机
{data.get('problem', '无').strip()}

## 📚 研究背景与相关工作  
{data.get('background', '无').strip()}

## 💡 创新点与思路来源
{data.get('innovation', '无').strip()}

## 🔧 技术方案与方法
{data.get('solution', '无').strip()}

## 🧪 实验设计与验证
{data.get('experiment', '无').strip()}

## 📊 结论与贡献
{data.get('conclusion', '无').strip()}

## 🚀 局限性与未来工作
{data.get('future_work', '无').strip()}

## ⚙️ 技术实现
{data.get('implementation', '无').strip()}

## 🌍 影响与应用
{data.get('impact', '无').strip()}

## 🤔 评价与思考
{data.get('evaluation', '无').strip()}

---
*分析模板版本: V2 - 深度结构化分析*
"""
            return markdown
            
        except yaml.YAMLError as e:
            return f"YAML解析错误: {e}\n\n原始内容:\n{content}"