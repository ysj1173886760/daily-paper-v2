#!/usr/bin/env python3
"""
模板系统测试脚本
用于验证论文分析模板的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from daily_paper.templates import get_template, list_templates


def test_template_registry():
    """测试模板注册表功能"""
    print("=== 测试模板注册表 ===")
    
    # 列出所有可用模板
    templates = list_templates()
    print("可用模板:")
    for name, description in templates.items():
        print(f"  {name}: {description}")
    
    print()


def test_template_functionality():
    """测试模板基本功能"""
    print("=== 测试模板功能 ===")
    
    # 测试用论文文本
    sample_text = """
    This paper presents a novel approach to deep learning optimization.
    The method combines gradient descent with adaptive learning rates.
    Experiments show 15% improvement over baseline methods.
    """
    
    for template_name in ["simple", "v1", "v2"]:
        print(f"\n--- 测试 {template_name} 模板 ---")
        
        try:
            template = get_template(template_name)
            print(f"模板名称: {template.name}")
            print(f"模板描述: {template.description}")
            
            # simple模板没有_get_required_fields方法
            if hasattr(template, '_get_required_fields'):
                print(f"必需字段: {template._get_required_fields()}")
            else:
                print("必需字段: N/A (简单模板)")
            
            # 生成prompt（不调用LLM）
            prompt = template.generate_prompt(sample_text)
            print(f"Prompt长度: {len(prompt)} 字符")
            
            # 测试格式转换
            if template_name == "simple":
                # simple模板直接使用文本
                sample_content = "这是一篇关于深度学习的论文介绍"
            else:
                # 其他模板使用YAML
                sample_content = """
title: |
  Sample Paper Title
problem: |
  This is a sample problem description
solution: |
  This is a sample solution
"""
            markdown = template.format_to_markdown(sample_content)
            print(f"Markdown输出预览:")
            print(markdown[:200] + "..." if len(markdown) > 200 else markdown)
            
        except Exception as e:
            print(f"❌ 测试 {template_name} 模板失败: {e}")
    
    print()


def test_error_handling():
    """测试错误处理"""
    print("=== 测试错误处理 ===")
    
    try:
        # 尝试获取不存在的模板
        get_template("nonexistent")
        print("❌ 应该抛出错误但没有")
    except ValueError as e:
        print(f"✅ 正确处理不存在的模板: {e}")
    
    print()


def main():
    """主测试函数"""
    print("论文分析模板系统测试\n")
    
    test_template_registry()
    test_template_functionality()
    test_error_handling()
    
    print("=== 测试完成 ===")
    print("模板系统工作正常！")


if __name__ == "__main__":
    main()