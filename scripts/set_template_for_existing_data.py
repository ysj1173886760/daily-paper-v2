#!/usr/bin/env python3
"""
设置现有数据的模板名称脚本

该脚本用于为现有的论文数据设置模板名称，方便管理不同时期使用的分析模板。

使用方法:
    python scripts/set_template_for_existing_data.py --config config/rag.yaml --template v2
    python scripts/set_template_for_existing_data.py --data-file data/daily_papers.parquet --template v1 --date-range 2024-01-01 2024-06-30
"""

import argparse
import sys
import os
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.config import Config
from daily_paper.templates import TemplateRegistry, get_template
from daily_paper.utils.logger import logger


def parse_date(date_str: str) -> date:
    """解析日期字符串"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"日期格式错误: {date_str}，应为 YYYY-MM-DD")


def set_template_by_date_range(paper_manager: PaperMetaManager, template_name: str, 
                               start_date: date = None, end_date: date = None) -> int:
    """
    根据日期范围设置模板
    
    Args:
        paper_manager: 论文管理器
        template_name: 模板名称
        start_date: 开始日期，None表示不限制
        end_date: 结束日期，None表示不限制
    
    Returns:
        更新的论文数量
    """
    all_papers = paper_manager.get_all_papers()
    
    # 过滤条件
    mask = True
    
    # 按日期过滤
    if start_date is not None:
        mask = mask & (all_papers['update_time'] >= start_date)
    if end_date is not None:
        mask = mask & (all_papers['update_time'] <= end_date)
    
    # 只更新没有模板信息的论文（template为None或NaN）
    mask = mask & (all_papers['template'].isna())
    
    filtered_papers = all_papers[mask]
    
    if len(filtered_papers) == 0:
        logger.info("没有找到符合条件且需要更新模板的论文")
        return 0
    
    logger.info(f"找到 {len(filtered_papers)} 篇需要更新模板的论文")
    
    # 准备更新数据
    updates = {}
    for _, row in filtered_papers.iterrows():
        paper_id = row['paper_id']
        updates[paper_id] = {'template': template_name}
    
    # 批量更新
    paper_manager.update_papers(updates)
    paper_manager.persist()
    
    return len(updates)


def set_template_by_summary_analysis(paper_manager: PaperMetaManager) -> dict:
    """
    根据摘要内容分析自动设置模板
    
    通过分析摘要的结构来推断使用的模板类型
    """
    all_papers = paper_manager.get_all_papers()
    
    # 只处理有摘要但没有模板信息的论文
    mask = (all_papers['summary'].notna()) & (all_papers['template'].isna())
    filtered_papers = all_papers[mask]
    
    if len(filtered_papers) == 0:
        logger.info("没有找到需要自动分析模板的论文")
        return {}
    
    logger.info(f"开始自动分析 {len(filtered_papers)} 篇论文的模板类型")
    
    updates = {}
    template_counts = {'v1': 0, 'v2': 0, 'simple': 0, 'unknown': 0}
    
    for _, row in filtered_papers.iterrows():
        paper_id = row['paper_id']
        summary = str(row['summary'])
        
        # 分析摘要内容判断模板类型
        template_name = analyze_summary_template(summary)
        
        if template_name != 'unknown':
            updates[paper_id] = {'template': template_name}
        
        template_counts[template_name] += 1
    
    if updates:
        paper_manager.update_papers(updates)
        paper_manager.persist()
        logger.info(f"成功更新 {len(updates)} 篇论文的模板信息")
    
    return template_counts


def analyze_summary_template(summary: str) -> str:
    """
    分析摘要内容判断使用的模板类型
    
    Args:
        summary: 论文摘要内容
        
    Returns:
        推断的模板名称: 'v1', 'v2', 'simple', 'unknown'
    """
    summary_lower = summary.lower()
    
    # V2模板特征：通常包含更多结构化字段
    v2_indicators = [
        'technical contribution',
        'methodology',
        'experimental setup',
        'baseline comparison',
        'limitations',
        'future work',
        'code availability',
        'reproducibility',
        'computational complexity',
        'scalability',
        'practical implications'
    ]
    
    # V1模板特征：经典8个维度
    v1_indicators = [
        'problem definition',
        'research motivation',
        'technical approach',
        'key innovation',
        'experimental results',
        'performance metrics',
        'related work',
        'conclusion'
    ]
    
    # Simple模板特征：简单结构
    simple_indicators = [
        '简介:', '方法:', '实验:', '结论:',
        'introduction', 'method', 'experiment', 'conclusion'
    ]
    
    # 统计匹配的指标数量
    v2_matches = sum(1 for indicator in v2_indicators if indicator in summary_lower)
    v1_matches = sum(1 for indicator in v1_indicators if indicator in summary_lower)
    simple_matches = sum(1 for indicator in simple_indicators if indicator in summary_lower)
    
    # 根据匹配数量判断模板类型
    if v2_matches >= 3:  # V2模板通常有更多结构化字段
        return 'v2'
    elif v1_matches >= 3:  # V1模板有经典的8个维度
        return 'v1'
    elif simple_matches >= 2:  # Simple模板结构简单
        return 'simple'
    elif len(summary) < 500:  # 短摘要可能是simple模板
        return 'simple'
    else:
        return 'unknown'


def show_template_statistics(paper_manager: PaperMetaManager):
    """显示模板使用统计"""
    all_papers = paper_manager.get_all_papers()
    
    print("\n=== 模板使用统计 ===")
    template_stats = all_papers['template'].value_counts(dropna=False)
    
    total_papers = len(all_papers)
    for template, count in template_stats.items():
        if pd.isna(template):
            template_name = "未设置"
        else:
            template_name = template
        percentage = (count / total_papers) * 100
        print(f"{template_name}: {count} 篇 ({percentage:.1f}%)")
    
    print(f"\n总计: {total_papers} 篇论文")


def main():
    parser = argparse.ArgumentParser(
        description="设置现有论文数据的模板名称",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用配置文件，为所有未设置模板的论文设置v2模板
  python scripts/set_template_for_existing_data.py --config config/rag.yaml --template v2

  # 直接指定数据文件，为特定日期范围的论文设置v1模板
  python scripts/set_template_for_existing_data.py --data-file data/daily_papers.parquet --template v1 --start-date 2024-01-01 --end-date 2024-06-30

  # 自动分析现有摘要内容来推断模板类型
  python scripts/set_template_for_existing_data.py --data-file data/daily_papers.parquet --auto-analyze

  # 只显示当前模板统计信息
  python scripts/set_template_for_existing_data.py --data-file data/daily_papers.parquet --stats-only
        """
    )
    
    # 数据源选项
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--config', '-c', help='配置文件路径')
    data_group.add_argument('--data-file', '-d', help='直接指定数据文件路径')
    
    # 模板设置选项
    template_group = parser.add_mutually_exclusive_group()
    template_group.add_argument('--template', '-t', help='要设置的模板名称 (simple, v1, v2)')
    template_group.add_argument('--auto-analyze', '-a', action='store_true', 
                               help='自动分析摘要内容来推断模板类型')
    
    # 过滤选项
    parser.add_argument('--start-date', type=parse_date, 
                       help='开始日期 (YYYY-MM-DD)，只处理此日期之后的论文')
    parser.add_argument('--end-date', type=parse_date, 
                       help='结束日期 (YYYY-MM-DD)，只处理此日期之前的论文')
    
    # 其他选项
    parser.add_argument('--stats-only', action='store_true', 
                       help='只显示统计信息，不进行任何修改')
    parser.add_argument('--dry-run', action='store_true', 
                       help='试运行，显示将要进行的操作但不实际执行')
    
    args = parser.parse_args()
    
    # 验证模板名称
    if args.template:
        if not TemplateRegistry.exists(args.template):
            available_templates = list(TemplateRegistry.list_templates().keys())
            print(f"错误: 模板 '{args.template}' 不存在")
            print(f"可用模板: {', '.join(available_templates)}")
            sys.exit(1)
    
    # 获取数据文件路径
    if args.config:
        config = Config.from_yaml(args.config)
        data_file = config.meta_file_path
        print(f"使用配置文件: {args.config}")
        print(f"数据文件: {data_file}")
    else:
        data_file = args.data_file
        print(f"数据文件: {data_file}")
    
    # 检查数据文件是否存在
    if not os.path.exists(data_file):
        print(f"错误: 数据文件不存在: {data_file}")
        sys.exit(1)
    
    # 创建论文管理器
    paper_manager = PaperMetaManager(data_file)
    
    # 显示统计信息
    import pandas as pd
    show_template_statistics(paper_manager)
    
    if args.stats_only:
        print("\n只显示统计信息，未进行任何修改。")
        return
    
    # 执行操作
    if args.auto_analyze:
        print("\n开始自动分析摘要内容...")
        if args.dry_run:
            print("【试运行模式】将会自动分析摘要内容来推断模板类型")
        else:
            template_counts = set_template_by_summary_analysis(paper_manager)
            print("\n自动分析结果:")
            for template, count in template_counts.items():
                print(f"  {template}: {count} 篇")
    
    elif args.template:
        print(f"\n开始设置模板为: {args.template}")
        
        # 显示过滤条件
        conditions = []
        if args.start_date:
            conditions.append(f"开始日期: {args.start_date}")
        if args.end_date:
            conditions.append(f"结束日期: {args.end_date}")
        
        if conditions:
            print(f"过滤条件: {', '.join(conditions)}")
        
        if args.dry_run:
            print("【试运行模式】将会设置符合条件的论文模板")
        else:
            updated_count = set_template_by_date_range(
                paper_manager, args.template, args.start_date, args.end_date
            )
            print(f"\n成功更新 {updated_count} 篇论文的模板为: {args.template}")
    
    else:
        print("\n请指定操作: --template, --auto-analyze, 或 --stats-only")
        return
    
    # 显示更新后的统计信息
    if not args.dry_run and not args.stats_only:
        print("\n更新后的统计信息:")
        show_template_statistics(paper_manager)
    
    print("\n完成！")


if __name__ == "__main__":
    main()