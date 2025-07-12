"""
YAML到Markdown转换器
用于将论文分析结果转换为适合推送的Markdown格式
"""

import yaml
from typing import Dict, Any
from daily_paper.utils.logger import logger


def yaml_to_markdown(yaml_str: str) -> str:
    """
    将YAML字符串转换为格式化的Markdown

    Args:
        yaml_str: YAML格式的字符串

    Returns:
        格式化的Markdown字符串
    """
    try:
        # 解析YAML
        data = yaml.safe_load(yaml_str)

        if not isinstance(data, dict):
            return f"```\n{yaml_str}\n```"

        # 定义字段标题映射
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
                content = str(data[field]).strip()

                # 特殊处理伪代码字段
                if field == "pseudocode":
                    markdown_parts.append(f"{title}\n```\n{content}\n```")
                else:
                    markdown_parts.append(f"{title}\n{content}")

        # 处理其他未预定义的字段
        for key, value in data.items():
            if key not in field_order and value:
                title = f"**{key.upper()}**"
                content = str(value).strip()
                markdown_parts.append(f"{title}\n{content}")

        return "\n\n".join(markdown_parts)

    except yaml.YAMLError as e:
        import traceback

        logger.error(f"YAML解析错误: {str(e)}. traceback: {traceback.format_exc()}")
        return f"❌ **YAML解析错误**\n```\n{str(e)}\n```\n\n**原始内容：**\n```\n{yaml_str}\n```"
    except Exception as e:
        return f"❌ **转换错误**\n```\n{str(e)}\n```\n\n**原始内容：**\n```\n{yaml_str}\n```"


def extract_yaml_from_text(text: str) -> str:
    """
    从文本中提取YAML部分

    Args:
        text: 包含YAML的文本

    Returns:
        提取的YAML字符串
    """
    # 查找YAML代码块
    yaml_start = text.find("```yaml")
    if yaml_start != -1:
        yaml_end = text.find("```", yaml_start + 7)
        if yaml_end != -1:
            return text[yaml_start + 7 : yaml_end].strip()

    # 如果没有找到YAML代码块，返回原文本
    return text


def format_paper_analysis(
    summary: str, paper_title: str = "", paper_url: str = ""
) -> str:
    """
    格式化论文分析结果为完整的Markdown

    Args:
        summary: 论文分析结果（可能包含YAML）
        paper_title: 论文标题
        paper_url: 论文URL

    Returns:
        格式化的Markdown字符串
    """
    markdown_parts = []

    # 添加论文标题
    if paper_title:
        markdown_parts.append(f"# {paper_title}")

    # 添加论文链接
    if paper_url:
        markdown_parts.append(f"🔗 [论文链接]({paper_url})")

    # 添加分隔线
    if paper_title or paper_url:
        markdown_parts.append("---")

    # 提取并转换YAML
    yaml_content = extract_yaml_from_text(summary)
    formatted_analysis = yaml_to_markdown(yaml_content)

    markdown_parts.append(formatted_analysis)

    return "\n\n".join(markdown_parts)


def create_daily_report_markdown(papers_data: list) -> str:
    """
    创建每日报告的Markdown格式

    Args:
        papers_data: 论文数据列表，每个元素包含 (title, url, summary)

    Returns:
        每日报告的Markdown字符串
    """
    from datetime import datetime

    # 报告标题
    today = datetime.now().strftime("%Y-%m-%d")
    markdown_parts = [f"# 📑 每日论文报告 - {today}", f"*共分析 {len(papers_data)} 篇论文*", "---"]

    # 添加每篇论文的分析
    for i, (title, url, summary) in enumerate(papers_data, 1):
        paper_section = [f"## {i}. {title}", f"🔗 [论文链接]({url})" if url else "", ""]

        # 提取并格式化YAML
        yaml_content = extract_yaml_from_text(summary)
        formatted_analysis = yaml_to_markdown(yaml_content)
        paper_section.append(formatted_analysis)

        markdown_parts.extend(paper_section)
        markdown_parts.append("---")

    return "\n\n".join(markdown_parts)


if __name__ == "__main__":
    # 测试用例
    test_yaml = """
```yaml
problem: |
  这篇论文主要解决深度学习模型在小数据集上的过拟合问题
background: |
  传统的深度学习模型需要大量数据才能达到良好的性能，在小数据集上容易过拟合
idea_source: |
  受到迁移学习和元学习的启发，提出了一种新的正则化方法
solution: |
  提出了一种自适应正则化技术，结合了数据增强和知识蒸馏
experiment: |
  在多个小数据集上进行了实验，包括CIFAR-10、MNIST等
conclusion: |
  实验结果表明，该方法在小数据集上的性能提升了15-20%
future_work: |
  未来可以探索在更大规模数据集上的应用，以及与其他正则化方法的结合
pseudocode: |
  for epoch in range(num_epochs):
      for batch in dataloader:
          loss = compute_loss(model(batch))
          reg_loss = adaptive_regularization(model)
          total_loss = loss + reg_loss
          total_loss.backward()
          optimizer.step()
```
"""

    print("=== 测试YAML到Markdown转换 ===")
    result = yaml_to_markdown(extract_yaml_from_text(test_yaml))
    print(result)
