#!/usr/bin/env python3
"""
基于最近一周数据估算最近一个月的cs分类论文统计
"""

import datetime
import time
import statistics
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stats_cs_ai_papers import (
    get_papers_by_date_range, 
    calculate_daily_stats,
    CS_CATEGORIES
)

# 主要的cs分类 - 扩展版本
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
    'cs.HC': 'Human-Computer Interaction',
    'cs.RO': 'Robotics',
    'cs.NE': 'Neural and Evolutionary Computing',
    'cs.DS': 'Data Structures and Algorithms',
    'cs.NI': 'Networking and Internet Architecture',
    'cs.SY': 'Systems and Control'
}


def estimate_monthly_from_weekly(weekly_data, weeks=4):
    """基于一周数据估算月数据"""
    return {
        'total_estimated': weekly_data['total'] * weeks,
        'avg_estimated': weekly_data['avg'],  # 日均不变
        'max_estimated': weekly_data['max'],  # 单日最高不变
        'p99_estimated': weekly_data['p99'],  # P99不变
        'weekly_total': weekly_data['total'],
        'weekly_avg': weekly_data['avg'],
        'active_days_week': weekly_data['active_days'],
        'estimated_active_days_month': min(weekly_data['active_days'] * weeks, 30)
    }


def batch_weekly_analysis():
    """快速分析一周数据用于月度估算"""
    
    print(f"🔍 基于最近7天数据估算最近30天统计...")
    print(f"📊 统计分类数: {len(MAJOR_CS_CATEGORIES)}")
    print("=" * 70)
    
    results = []
    
    for i, (category, name) in enumerate(MAJOR_CS_CATEGORIES.items(), 1):
        try:
            print(f"[{i:2}/{len(MAJOR_CS_CATEGORIES)}] {category} ({name[:25]})...", end=" ")
            
            # 获取一周数据
            papers_by_date = get_papers_by_date_range(category, days=7, max_results=300)
            weekly_stats = calculate_daily_stats(papers_by_date, 7)
            
            # 估算月度数据
            monthly_est = estimate_monthly_from_weekly(weekly_stats, weeks=4)
            
            result = {
                'category': category,
                'name': name,
                'weekly_total': weekly_stats.get('total', 0),
                'weekly_avg': weekly_stats.get('avg', 0.0),
                'weekly_max': weekly_stats.get('max', 0),
                'weekly_p99': weekly_stats.get('p99', 0),
                'weekly_active_days': weekly_stats.get('active_days', 0),
                'monthly_total_est': monthly_est['total_estimated'],
                'monthly_avg_est': monthly_est['avg_estimated'],
                'monthly_max_est': monthly_est['max_estimated'],
                'monthly_p99_est': monthly_est['p99_estimated'],
            }
            
            results.append(result)
            print(f"7天: {result['weekly_total']}篇 → 30天估算: {result['monthly_total_est']}篇")
            
        except Exception as e:
            print(f"❌ 错误: {str(e)[:30]}...")
            results.append({
                'category': category, 'name': name,
                'weekly_total': 0, 'weekly_avg': 0.0, 'weekly_max': 0, 'weekly_p99': 0,
                'weekly_active_days': 0, 'monthly_total_est': 0, 'monthly_avg_est': 0.0,
                'monthly_max_est': 0, 'monthly_p99_est': 0,
            })
    
    return results


def print_monthly_estimate_report(results):
    """打印月度估算报告"""
    
    valid_results = [r for r in results if r['weekly_total'] > 0]
    
    print(f"\n📊 cs分类论文数量统计 - 最近30天估算报告")
    print("=" * 100)
    
    print(f"\n💡 说明: 基于最近7天真实数据估算30天总量 (7天数据 × 4)")
    print("-" * 100)
    
    # 按月度估算总量排序
    sorted_by_monthly = sorted(valid_results, key=lambda x: x['monthly_total_est'], reverse=True)
    
    print(f"\n🏆 TOP 15 - 按月度估算论文总数排序:")
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'7天实际':<8} {'30天估算':<8} {'日均':<6} {'最高':<5} {'P99':<4}")
    print("-" * 100)
    
    for i, r in enumerate(sorted_by_monthly[:15], 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_total']:<8} {r['monthly_total_est']:<8} {r['weekly_avg']:<6.1f} {r['weekly_max']:<5} {r['weekly_p99']:<4}")
    
    # 按日均排序
    print(f"\n📈 TOP 10 - 按日均论文数排序:")
    sorted_by_avg = sorted(valid_results, key=lambda x: x['weekly_avg'], reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'日均':<6} {'7天':<6} {'30天估算':<8}")
    print("-" * 90)
    
    for i, r in enumerate(sorted_by_avg[:10], 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_avg']:<6.1f} {r['weekly_total']:<6} {r['monthly_total_est']:<8}")
    
    # 按单日最高排序
    print(f"\n🔥 TOP 10 - 按单日最高论文数排序:")
    sorted_by_max = sorted(valid_results, key=lambda x: x['weekly_max'], reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'单日最高':<8} {'日均':<6} {'30天估算':<8}")
    print("-" * 90)
    
    for i, r in enumerate(sorted_by_max[:10], 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_max']:<8} {r['weekly_avg']:<6.1f} {r['monthly_total_est']:<8}")
    
    # 全局统计汇总
    print(f"\n📋 全局统计汇总:")
    print("-" * 60)
    
    if valid_results:
        # 7天实际数据统计
        weekly_totals = [r['weekly_total'] for r in valid_results]
        weekly_avgs = [r['weekly_avg'] for r in valid_results]
        weekly_maxs = [r['weekly_max'] for r in valid_results]
        weekly_p99s = [r['weekly_p99'] for r in valid_results]
        
        # 30天估算数据统计
        monthly_totals_est = [r['monthly_total_est'] for r in valid_results]
        
        print(f"统计分类数: {len(valid_results)}/{len(MAJOR_CS_CATEGORIES)} 个")
        print(f"")
        print(f"📊 7天实际数据:")
        print(f"  论文总数: {sum(weekly_totals):,} 篇")
        print(f"  各分类平均: {statistics.mean(weekly_totals):.0f} 篇")
        print(f"  最高单分类: {max(weekly_totals)} 篇 ({sorted_by_monthly[0]['category']})")
        print(f"  日均最高: {max(weekly_avgs):.1f} 篇/天 ({sorted_by_avg[0]['category']})")
        print(f"  单日最高: {max(weekly_maxs)} 篇 ({sorted_by_max[0]['category']})")
        print(f"  最高P99: {max(weekly_p99s)} 篇")
        print(f"")
        print(f"📅 30天估算数据:")
        print(f"  论文总数: {sum(monthly_totals_est):,} 篇 (基于7天数据×4)")
        print(f"  各分类平均: {statistics.mean(monthly_totals_est):.0f} 篇")
        print(f"  最高单分类: {max(monthly_totals_est):,} 篇 ({sorted_by_monthly[0]['category']})")
        
        # 全局统计
        print(f"")
        print(f"🔢 横向对比 (所有分类合计):")
        total_7day = sum(weekly_totals)
        total_30day_est = sum(monthly_totals_est)
        avg_daily_all = total_7day / 7
        print(f"  7天总计: {total_7day:,} 篇")
        print(f"  30天估算: {total_30day_est:,} 篇") 
        print(f"  全分类日均: {avg_daily_all:.0f} 篇/天")
        print(f"  估算倍数: {total_30day_est/total_7day:.1f}x")


def main():
    try:
        start_time = time.time()
        
        print("🚀 开始快速估算cs分类30天论文统计...\n")
        
        # 基于一周数据快速分析
        results = batch_weekly_analysis()
        
        # 打印估算报告
        print_monthly_estimate_report(results)
        
        # 统计耗时
        elapsed = time.time() - start_time
        print(f"\n⏱️  统计完成，耗时: {elapsed:.1f} 秒")
        
        print(f"\n💡 提示: 此估算基于最近7天实际数据，实际30天数据可能因节假日、会议截止日期等因素有所差异")
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 统计错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()