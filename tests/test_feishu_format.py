#!/usr/bin/env python3
"""
测试飞书消息格式

验证日报推送到飞书的消息格式是否正确
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_paper.nodes.push_daily_report_to_feishu_node import PushDailyReportToFeishuNode
import json


def test_feishu_message_format():
    """测试飞书消息格式"""
    node = PushDailyReportToFeishuNode()
    
    # 模拟报告内容
    test_report = """# 📊 AI论文日报 - 2025年1月15日

## 📈 今日概览
- **论文总数**: 5篇
- **推荐论文**: 3篇
- **主要领域**: RAG, Knowledge Graph

## 🔍 趋势分析
今日论文主要关注检索增强生成技术的最新发展，特别是在多模态场景下的应用。

## ⭐ 推荐论文

### 1. 多模态检索增强生成的新方法
**推荐理由**: 该论文提出了创新的多模态RAG架构
**核心亮点**: 多模态融合 | 高效检索 | 性能提升

## 📋 完整论文列表
📄 **1. 多模态检索增强生成的新方法**
   - 作者: Zhang Wei
   - 链接: https://arxiv.org/abs/2501.001
"""
    
    # 构建飞书消息
    feishu_message = node._build_feishu_message(test_report)
    
    print("🔍 飞书消息格式预览:")
    print(json.dumps(feishu_message, ensure_ascii=False, indent=2))
    
    # 验证消息结构
    required_fields = ["msg_type", "card"]
    card_fields = ["elements", "header"]
    
    print("\n✅ 格式验证:")
    
    for field in required_fields:
        if field in feishu_message:
            print(f"  ✓ {field}: 存在")
        else:
            print(f"  ✗ {field}: 缺失")
    
    if "card" in feishu_message:
        card = feishu_message["card"]
        for field in card_fields:
            if field in card:
                print(f"  ✓ card.{field}: 存在")
            else:
                print(f"  ✗ card.{field}: 缺失")
    
    # 检查内容长度
    content = feishu_message["card"]["elements"][0]["text"]["content"]
    print(f"\n📊 内容统计:")
    print(f"  - 内容长度: {len(content)} 字符")
    print(f"  - 行数: {content.count('\\n') + 1} 行")
    
    return feishu_message


if __name__ == "__main__":
    print("🧪 测试飞书消息格式")
    test_feishu_message_format()
    print("\n✅ 测试完成")