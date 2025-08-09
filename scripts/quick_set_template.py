#!/usr/bin/env python3
"""
快速设置现有数据模板的简单脚本

使用方法:
    # 为所有未设置模板的论文设置v2模板
    python scripts/quick_set_template.py v2

    # 为指定数据文件的论文设置v1模板  
    python scripts/quick_set_template.py v1 data/rag.parquet

    # 显示当前模板统计
    python scripts/quick_set_template.py --stats
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.templates import TemplateRegistry
import pandas as pd


def show_template_statistics(paper_manager: PaperMetaManager):
    """显示模板使用统计"""
    all_papers = paper_manager.get_all_papers()
    
    print("=== 当前模板使用统计 ===")
    template_stats = all_papers['template'].value_counts(dropna=False)
    
    total_papers = len(all_papers)
    for template, count in template_stats.items():
        if pd.isna(template):
            template_name = "未设置"
        else:
            template_name = template
        percentage = (count / total_papers) * 100
        print(f"{template_name}: {count:4d} 篇 ({percentage:5.1f}%)")
    
    print(f"{'='*30}")
    print(f"总计: {total_papers} 篇论文")


def set_template_for_unset_papers(paper_manager: PaperMetaManager, template_name: str):
    """为所有未设置模板的论文设置指定模板"""
    all_papers = paper_manager.get_all_papers()
    
    # 找到没有模板设置的论文
    unset_mask = all_papers['template'].isna()
    unset_papers = all_papers[unset_mask]
    
    if len(unset_papers) == 0:
        print("✅ 所有论文都已设置模板，无需更新")
        return 0
    
    print(f"📝 找到 {len(unset_papers)} 篇未设置模板的论文")
    
    # 准备更新数据
    updates = {}
    for _, row in unset_papers.iterrows():
        paper_id = row['paper_id']
        updates[paper_id] = {'template': template_name}
    
    # 执行更新
    paper_manager.update_papers(updates)
    paper_manager.persist()
    
    print(f"✅ 成功为 {len(updates)} 篇论文设置模板: {template_name}")
    return len(updates)


def main():
    # 默认数据文件
    default_data_file = "data/daily_papers.parquet"
    
    if len(sys.argv) == 1:
        print("用法:")
        print(f"  python {sys.argv[0]} <template_name> [data_file]")
        print(f"  python {sys.argv[0]} --stats [data_file]")
        print(f"\n示例:")
        print(f"  python {sys.argv[0]} v2")
        print(f"  python {sys.argv[0]} v1 data/rag.parquet")
        print(f"  python {sys.argv[0]} --stats")
        print(f"\n可用模板:")
        templates = TemplateRegistry.list_templates()
        for name, desc in templates.items():
            print(f"  {name}: {desc}")
        return
    
    # 处理参数
    if sys.argv[1] == "--stats":
        # 只显示统计信息
        data_file = sys.argv[2] if len(sys.argv) > 2 else default_data_file
        
        if not os.path.exists(data_file):
            print(f"❌ 错误: 数据文件不存在: {data_file}")
            return
        
        print(f"📊 数据文件: {data_file}")
        paper_manager = PaperMetaManager(data_file)
        show_template_statistics(paper_manager)
        return
    
    # 设置模板
    template_name = sys.argv[1]
    data_file = sys.argv[2] if len(sys.argv) > 2 else default_data_file
    
    # 验证模板名称
    if not TemplateRegistry.exists(template_name):
        available_templates = list(TemplateRegistry.list_templates().keys())
        print(f"❌ 错误: 模板 '{template_name}' 不存在")
        print(f"可用模板: {', '.join(available_templates)}")
        return
    
    # 检查数据文件
    if not os.path.exists(data_file):
        print(f"❌ 错误: 数据文件不存在: {data_file}")
        return
    
    print(f"🔧 设置模板: {template_name}")
    print(f"📄 数据文件: {data_file}")
    print("-" * 50)
    
    # 创建管理器并显示当前状态
    paper_manager = PaperMetaManager(data_file)
    show_template_statistics(paper_manager)
    
    print()
    
    # 执行设置
    updated_count = set_template_for_unset_papers(paper_manager, template_name)
    
    if updated_count > 0:
        print("\n更新后的统计:")
        show_template_statistics(paper_manager)
    
    print(f"\n🎉 操作完成！")


if __name__ == "__main__":
    main()