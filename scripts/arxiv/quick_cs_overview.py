#!/usr/bin/env python3
"""
快速统计主要cs分类的论文数量概览
"""

import datetime
from typing import Dict, List, NamedTuple
import logging
import sys
from pathlib import Path
import time
import statistics

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stats_cs_ai_papers import (
    get_papers_by_date_range, 
    calculate_daily_stats,
    format_date_chinese
)

# 设置日志
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
logger = logging.getLogger(__name__)

# 主要的cs分类
MAJOR_CS_CATEGORIES = {
    'cs.AI': 'Artificial Intelligence',
    'cs.LG': 'Machine Learning', 
    'cs.CV': 'Computer Vision',
    'cs.CL': 'Computation and Language',
    'cs.IR': 'Information Retrieval',
    'cs.CR': 'Cryptography and Security',
    'cs.SE': 'Software Engineering',
    'cs.DC': 'Distributed Computing',
    'cs.DB': 'Databases',
    'cs.HC': 'Human-Computer Interaction'
}


def quick_stats_overview(days: int = 30, max_results: int = 800):
    """快速统计主要cs分类"""
    
    print(f"🚀 快速统计主要cs分类最近 {days} 天的论文数量...")
    print(f"📊 统计分类数: {len(MAJOR_CS_CATEGORIES)}")
    print("=" * 70)
    
    results = []
    
    for i, (category, name) in enumerate(MAJOR_CS_CATEGORIES.items(), 1):
        try:
            print(f"[{i}/{len(MAJOR_CS_CATEGORIES)}] {category} ({name})...", end=" ")
            
            # 获取论文数据
            papers_by_date = get_papers_by_date_range(category, days, max_results)
            stats = calculate_daily_stats(papers_by_date, days)
            
            result = {
                'category': category,
                'name': name,
                'total': int(stats.get('total', 0)),
                'avg': stats.get('avg', 0.0),
                'max': int(stats.get('max', 0)),
                'p99': int(stats.get('p99', 0)),
                'active_days': int(stats.get('active_days', 0))
            }
            
            results.append(result)
            print(f"✅ 总计: {result['total']}, avg: {result['avg']:.1f}, max: {result['max']}, p99: {result['p99']}")
            
        except Exception as e:
            print(f"❌ 错误: {str(e)[:50]}...")
            results.append({
                'category': category, 'name': name, 'total': 0, 'avg': 0.0, 
                'max': 0, 'p99': 0, 'active_days': 0
            })
    
    return results


def print_summary_report(results: List[Dict], days: int):
    """打印汇总报告"""
    
    # 过滤有效数据
    valid_results = [r for r in results if r['total'] > 0]
    
    print(f"\n📊 cs分类论文统计汇总 - 最近 {days} 天")
    print("=" * 80)
    
    # 详细表格
    print(f"\n{'分类':<8} {'名称':<25} {'总数':<6} {'日均':<6} {'最高':<5} {'P99':<4} {'活跃天':<6}")
    print("-" * 80)
    
    for r in sorted(valid_results, key=lambda x: x['total'], reverse=True):
        name = r['name'][:22] + '...' if len(r['name']) > 25 else r['name']
        print(f"{r['category']:<8} {name:<25} {r['total']:<6} {r['avg']:<6.1f} {r['max']:<5} {r['p99']:<4} {r['active_days']:<6}")
    
    # 全局统计
    print(f"\n📈 全局统计:")
    print("-" * 40)
    
    if valid_results:
        totals = [r['total'] for r in valid_results]
        avgs = [r['avg'] for r in valid_results]
        maxs = [r['max'] for r in valid_results]
        p99s = [r['p99'] for r in valid_results]
        
        print(f"总论文数: {sum(totals):,} 篇")
        print(f"分类数量: {len(valid_results)} 个")
        print(f"")
        print(f"各分类总数统计:")
        print(f"  平均: {statistics.mean(totals):.0f} 篇")
        print(f"  中位数: {statistics.median(totals):.0f} 篇") 
        print(f"  最大: {max(totals)} 篇 ({[r['category'] for r in valid_results if r['total'] == max(totals)][0]})")
        print(f"  最小: {min(totals)} 篇")
        print(f"")
        print(f"日均论文数统计:")
        print(f"  平均: {statistics.mean(avgs):.1f} 篇/天")
        print(f"  最大: {max(avgs):.1f} 篇/天 ({[r['category'] for r in valid_results if r['avg'] == max(avgs)][0]})")
        print(f"")
        print(f"单日最高论文数统计:")
        print(f"  平均: {statistics.mean(maxs):.0f} 篇")
        print(f"  最大: {max(maxs)} 篇 ({[r['category'] for r in valid_results if r['max'] == max(maxs)][0]})")
        print(f"")
        print(f"P99统计:")
        print(f"  平均: {statistics.mean(p99s):.0f} 篇")
        print(f"  最大: {max(p99s)} 篇 ({[r['category'] for r in valid_results if r['p99'] == max(p99s)][0]})")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='快速统计主要cs分类的论文数量')
    parser.add_argument('--days', type=int, default=30, help='统计天数，默认30天')
    parser.add_argument('--max-results', type=int, default=800, help='每分类最大论文数，默认800')
    
    args = parser.parse_args()
    
    try:
        start_time = time.time()
        
        # 快速统计
        results = quick_stats_overview(args.days, args.max_results)
        
        # 打印报告
        print_summary_report(results, args.days)
        
        # 统计耗时
        elapsed = time.time() - start_time
        print(f"\n⏱️  统计完成，耗时: {elapsed:.1f} 秒")
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 统计错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()