#!/usr/bin/env python3
"""
批量统计所有cs分类最近一个月的论文数量

提供综合的统计分析报告
"""

import datetime
from typing import Dict, List, NamedTuple
import logging
import sys
from pathlib import Path
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入现有脚本的功能
from stats_cs_ai_papers import (
    CS_CATEGORIES, 
    get_papers_by_date_range, 
    calculate_daily_stats,
    format_date_chinese
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CategoryStats(NamedTuple):
    """分类统计信息"""
    category: str
    name: str
    total: int
    avg: float
    median: float
    max: int
    min: int
    p99: int
    std: float
    active_days: int
    active_avg: float


def batch_analyze_cs_categories(days: int = 30, max_results: int = 2000, delay: int = 5) -> List[CategoryStats]:
    """
    批量分析所有cs分类
    
    Args:
        days: 统计天数
        max_results: 每个分类的最大论文数量
        delay: 每次请求之间的延迟秒数
        
    Returns:
        所有分类的统计信息列表
    """
    results = []
    total_categories = len(CS_CATEGORIES)
    
    print(f"🚀 开始批量统计 {total_categories} 个cs分类最近 {days} 天的论文数量...")
    print(f"📝 每次请求间隔: {delay}秒，单分类最大论文数: {max_results}")
    print("=" * 70)
    
    for i, (category, name) in enumerate(CS_CATEGORIES.items(), 1):
        try:
            print(f"\n[{i}/{total_categories}] 正在统计 {category} ({name})...")
            
            # 获取论文数据
            papers_by_date = get_papers_by_date_range(category, days, max_results)
            
            # 计算统计信息
            stats = calculate_daily_stats(papers_by_date, days)
            
            # 创建分类统计对象
            cat_stats = CategoryStats(
                category=category,
                name=name,
                total=int(stats.get('total', 0)),
                avg=stats.get('avg', 0.0),
                median=stats.get('median', 0.0),
                max=int(stats.get('max', 0)),
                min=int(stats.get('min', 0)),
                p99=int(stats.get('p99', 0)),
                std=stats.get('std', 0.0),
                active_days=int(stats.get('active_days', 0)),
                active_avg=stats.get('active_avg', 0.0)
            )
            
            results.append(cat_stats)
            
            print(f"✅ {category}: 总计 {cat_stats.total} 篇，avg={cat_stats.avg:.1f}, max={cat_stats.max}, p99={cat_stats.p99}")
            
            # 请求间延迟，避免API限制
            if i < total_categories:
                print(f"⏰ 等待 {delay} 秒...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"统计 {category} 时发生错误: {e}")
            # 创建空统计对象
            cat_stats = CategoryStats(
                category=category,
                name=name,
                total=0, avg=0.0, median=0.0, max=0, min=0, p99=0, std=0.0,
                active_days=0, active_avg=0.0
            )
            results.append(cat_stats)
            continue
    
    return results


def print_comprehensive_report(results: List[CategoryStats], days: int):
    """
    打印综合统计报告
    """
    # 过滤掉无数据的分类
    valid_results = [r for r in results if r.total > 0]
    
    print(f"\n📊 cs分类论文数量统计报告 - 最近 {days} 天")
    print("=" * 80)
    
    # 按总论文数排序
    sorted_by_total = sorted(valid_results, key=lambda x: x.total, reverse=True)
    
    print("\n🏆 TOP 10 - 按总论文数排序:")
    print(f"{'排名':<4} {'分类':<8} {'名称':<35} {'总数':<6} {'avg':<6} {'max':<5} {'p99':<5}")
    print("-" * 80)
    
    for i, stats in enumerate(sorted_by_total[:10], 1):
        name = stats.name[:32] + '...' if len(stats.name) > 35 else stats.name
        print(f"{i:<4} {stats.category:<8} {name:<35} {stats.total:<6} {stats.avg:<6.1f} {stats.max:<5} {stats.p99:<5}")
    
    # 按平均值排序
    print(f"\n📈 TOP 10 - 按日均论文数排序:")
    sorted_by_avg = sorted(valid_results, key=lambda x: x.avg, reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<35} {'日均':<6} {'总数':<6} {'max':<5}")
    print("-" * 80)
    
    for i, stats in enumerate(sorted_by_avg[:10], 1):
        name = stats.name[:32] + '...' if len(stats.name) > 35 else stats.name
        print(f"{i:<4} {stats.category:<8} {name:<35} {stats.avg:<6.1f} {stats.total:<6} {stats.max:<5}")
    
    # 按最大值排序
    print(f"\n🔥 TOP 10 - 按单日最高论文数排序:")
    sorted_by_max = sorted(valid_results, key=lambda x: x.max, reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<35} {'最高':<6} {'总数':<6} {'avg':<6}")
    print("-" * 80)
    
    for i, stats in enumerate(sorted_by_max[:10], 1):
        name = stats.name[:32] + '...' if len(stats.name) > 35 else stats.name
        print(f"{i:<4} {stats.category:<8} {name:<35} {stats.max:<6} {stats.total:<6} {stats.avg:<6.1f}")
    
    # 综合统计
    print(f"\n📋 全局统计概览:")
    print("-" * 50)
    
    if valid_results:
        total_papers = sum(r.total for r in valid_results)
        avg_totals = [r.total for r in valid_results]
        avg_avgs = [r.avg for r in valid_results]
        all_maxs = [r.max for r in valid_results]
        all_p99s = [r.p99 for r in valid_results]
        
        print(f"有效分类数: {len(valid_results)}/{len(results)}")
        print(f"论文总数: {total_papers:,} 篇")
        print(f"分类平均论文数: {sum(avg_totals)/len(avg_totals):.1f} 篇")
        print(f"最高单分类总数: {max(avg_totals):,} 篇 ({sorted_by_total[0].category})")
        print(f"最高日均论文数: {max(avg_avgs):.1f} 篇/天 ({sorted_by_avg[0].category})")
        print(f"最高单日论文数: {max(all_maxs)} 篇 ({sorted_by_max[0].category})")
        print(f"最高P99值: {max(all_p99s)} 篇")
    
    # 无数据的分类
    no_data_categories = [r for r in results if r.total == 0]
    if no_data_categories:
        print(f"\n❌ 无数据的分类 ({len(no_data_categories)} 个):")
        for cat in no_data_categories:
            print(f"  {cat.category} - {cat.name}")


def export_to_csv(results: List[CategoryStats], filename: str, days: int):
    """导出详细结果到CSV"""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'category', 'name', 'total_papers', 'avg_per_day', 'median', 
            'max_single_day', 'min_single_day', 'p99', 'std_dev', 
            'active_days', 'active_days_avg', 'stats_period_days'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for stats in sorted(results, key=lambda x: x.total, reverse=True):
            writer.writerow({
                'category': stats.category,
                'name': stats.name,
                'total_papers': stats.total,
                'avg_per_day': stats.avg,
                'median': stats.median,
                'max_single_day': stats.max,
                'min_single_day': stats.min,
                'p99': stats.p99,
                'std_dev': stats.std,
                'active_days': stats.active_days,
                'active_days_avg': stats.active_avg,
                'stats_period_days': days
            })
    
    logger.info(f"详细统计数据已导出到: {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='批量统计所有cs分类的论文数量',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/batch_cs_stats.py                     # 统计最近30天
  python scripts/batch_cs_stats.py --days 7           # 统计最近7天
  python scripts/batch_cs_stats.py --export report.csv # 导出详细数据
        """
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='统计天数，默认30天'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        default=2000,
        help='每个分类的最大论文数，默认2000'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=5,
        help='请求间隔秒数，默认5秒'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        help='导出详细数据到CSV文件'
    )
    
    args = parser.parse_args()
    
    try:
        start_time = time.time()
        
        # 批量分析
        results = batch_analyze_cs_categories(args.days, args.max_results, args.delay)
        
        # 打印报告
        print_comprehensive_report(results, args.days)
        
        # 导出CSV
        if args.export:
            export_to_csv(results, args.export, args.days)
        
        # 统计耗时
        elapsed = time.time() - start_time
        print(f"\n⏱️  统计完成，耗时: {elapsed/60:.1f} 分钟")
        
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断统计")
        sys.exit(1)
    except Exception as e:
        logger.error(f"批量统计过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()