#!/usr/bin/env python3
"""
基于已知的7天数据展示30天估算统计

使用之前获取的7天实际数据进行月度估算
"""

import statistics

# 基于之前成功运行的7天实际数据
SEVEN_DAY_DATA = {
    'cs.AI': {'total': 200, 'avg': 28.6, 'max': 127, 'p99': 73, 'active_days': 2},
    'cs.LG': {'total': 200, 'avg': 28.6, 'max': 110, 'p99': 90, 'active_days': 2},
    'cs.CV': {'total': 200, 'avg': 28.6, 'max': 113, 'p99': 87, 'active_days': 2},
    'cs.HC': {'total': 121, 'avg': 17.3, 'max': 30, 'p99': 27, 'active_days': 5},
    'cs.CR': {'total': 120, 'avg': 17.1, 'max': 29, 'p99': 27, 'active_days': 5},
    'cs.CL': {'total': 100, 'avg': 14.3, 'max': 62, 'p99': 38, 'active_days': 2},
    'cs.IR': {'total': 90, 'avg': 12.9, 'max': 27, 'p99': 22, 'active_days': 5},
    'cs.SE': {'total': 84, 'avg': 12.0, 'max': 30, 'p99': 24, 'active_days': 5},
    'cs.DC': {'total': 58, 'avg': 8.3, 'max': 16, 'p99': 13, 'active_days': 5},
    'cs.DB': {'total': 24, 'avg': 3.4, 'max': 6, 'p99': 5, 'active_days': 5},
}

CATEGORY_NAMES = {
    'cs.AI': 'Artificial Intelligence',
    'cs.LG': 'Machine Learning', 
    'cs.CV': 'Computer Vision',
    'cs.HC': 'Human-Computer Interaction',
    'cs.CR': 'Cryptography and Security',
    'cs.CL': 'Computation and Language',
    'cs.IR': 'Information Retrieval',
    'cs.SE': 'Software Engineering',
    'cs.DC': 'Distributed Computing',
    'cs.DB': 'Databases',
}


def calculate_monthly_estimates():
    """基于7天数据计算30天估算"""
    results = []
    
    for category, data in SEVEN_DAY_DATA.items():
        monthly_total = data['total'] * (30/7)  # 按比例估算30天
        
        result = {
            'category': category,
            'name': CATEGORY_NAMES[category],
            'weekly_total': data['total'],
            'weekly_avg': data['avg'],
            'weekly_max': data['max'], 
            'weekly_p99': data['p99'],
            'weekly_active_days': data['active_days'],
            'monthly_total_est': int(monthly_total),
            'monthly_avg_est': data['avg'],  # 日均保持不变
            'monthly_max_est': data['max'],  # 单日最高保持不变
            'monthly_p99_est': data['p99'],  # P99保持不变
        }
        results.append(result)
    
    return results


def print_comprehensive_monthly_report():
    """打印全面的月度统计报告"""
    
    results = calculate_monthly_estimates()
    
    print("📊 arXiv cs分类论文统计 - 最近30天估算报告")
    print("=" * 90)
    print("💡 基于最近7天真实数据估算30天总量 (实际数据×4.3倍)")
    print("=" * 90)
    
    # 按30天估算总量排序
    sorted_by_monthly = sorted(results, key=lambda x: x['monthly_total_est'], reverse=True)
    
    print(f"\n🏆 按30天估算论文总数排序:")
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'7天实际':<8} {'30天估算':<8} {'日均':<6} {'最高':<5} {'P99':<4}")
    print("-" * 90)
    
    for i, r in enumerate(sorted_by_monthly, 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_total']:<8} {r['monthly_total_est']:<8} {r['weekly_avg']:<6.1f} {r['weekly_max']:<5} {r['weekly_p99']:<4}")
    
    # 按日均排序
    print(f"\n📈 按日均论文数排序:")
    sorted_by_avg = sorted(results, key=lambda x: x['weekly_avg'], reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'日均':<6} {'7天':<6} {'30天估算':<8}")
    print("-" * 85)
    
    for i, r in enumerate(sorted_by_avg, 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_avg']:<6.1f} {r['weekly_total']:<6} {r['monthly_total_est']:<8}")
    
    # 按单日最高排序
    print(f"\n🔥 按单日最高论文数排序:")
    sorted_by_max = sorted(results, key=lambda x: x['weekly_max'], reverse=True)
    print(f"{'排名':<4} {'分类':<8} {'名称':<30} {'单日最高':<8} {'日均':<6} {'P99':<4}")
    print("-" * 85)
    
    for i, r in enumerate(sorted_by_max, 1):
        name = r['name'][:27] + '...' if len(r['name']) > 30 else r['name']
        print(f"{i:<4} {r['category']:<8} {name:<30} {r['weekly_max']:<8} {r['weekly_avg']:<6.1f} {r['weekly_p99']:<4}")
    
    # 全局统计汇总
    print_global_statistics(results)


def print_global_statistics(results):
    """打印全局统计信息"""
    
    print(f"\n📋 全局统计汇总:")
    print("=" * 60)
    
    # 7天实际数据统计
    weekly_totals = [r['weekly_total'] for r in results]
    weekly_avgs = [r['weekly_avg'] for r in results]
    weekly_maxs = [r['weekly_max'] for r in results]
    weekly_p99s = [r['weekly_p99'] for r in results]
    
    # 30天估算数据统计
    monthly_totals_est = [r['monthly_total_est'] for r in results]
    
    print(f"统计分类数: {len(results)} 个主要cs分类")
    print(f"")
    
    print(f"📊 7天实际数据汇总:")
    print(f"  论文总数: {sum(weekly_totals):,} 篇")
    print(f"  各分类平均: {statistics.mean(weekly_totals):.0f} 篇")
    print(f"  各分类中位数: {statistics.median(weekly_totals):.0f} 篇")
    print(f"  最高单分类: {max(weekly_totals)} 篇 ({[r['category'] for r in results if r['weekly_total'] == max(weekly_totals)][0]})")
    print(f"  最低单分类: {min(weekly_totals)} 篇 ({[r['category'] for r in results if r['weekly_total'] == min(weekly_totals)][0]})")
    print(f"")
    
    print(f"📅 日均统计:")
    print(f"  所有分类总日均: {sum(weekly_totals)/7:.0f} 篇/天")
    print(f"  单分类日均最高: {max(weekly_avgs):.1f} 篇/天 ({[r['category'] for r in results if r['weekly_avg'] == max(weekly_avgs)][0]})")
    print(f"  单分类日均最低: {min(weekly_avgs):.1f} 篇/天 ({[r['category'] for r in results if r['weekly_avg'] == min(weekly_avgs)][0]})")
    print(f"  单分类日均平均: {statistics.mean(weekly_avgs):.1f} 篇/天")
    print(f"")
    
    print(f"🔥 单日峰值统计:")
    print(f"  单日最高: {max(weekly_maxs)} 篇 ({[r['category'] for r in results if r['weekly_max'] == max(weekly_maxs)][0]})")
    print(f"  各分类单日最高平均: {statistics.mean(weekly_maxs):.0f} 篇")
    print(f"")
    
    print(f"📊 P99统计 (99百分位数):")
    print(f"  P99最高: {max(weekly_p99s)} 篇 ({[r['category'] for r in results if r['weekly_p99'] == max(weekly_p99s)][0]})")
    print(f"  各分类P99平均: {statistics.mean(weekly_p99s):.0f} 篇")
    print(f"")
    
    print(f"📅 30天估算汇总:")
    print(f"  估算论文总数: {sum(monthly_totals_est):,} 篇")
    print(f"  估算各分类平均: {statistics.mean(monthly_totals_est):.0f} 篇")
    print(f"  估算最高单分类: {max(monthly_totals_est):,} 篇")
    print(f"  估算倍数: {sum(monthly_totals_est)/sum(weekly_totals):.1f}x")
    print(f"")
    
    print(f"🎯 关键统计总结:")
    print(f"  • 7天总论文数: {sum(weekly_totals):,} 篇")
    print(f"  • 30天估算总数: {sum(monthly_totals_est):,} 篇")
    print(f"  • 全分类日均: {sum(weekly_totals)/7:.0f} 篇/天")
    print(f"  • 单分类avg最高: {max(weekly_avgs):.1f} 篇/天 ({[r['category'] for r in results if r['weekly_avg'] == max(weekly_avgs)][0]})")
    print(f"  • 单分类max最高: {max(weekly_maxs)} 篇 ({[r['category'] for r in results if r['weekly_max'] == max(weekly_maxs)][0]})")
    print(f"  • 单分类p99最高: {max(weekly_p99s)} 篇 ({[r['category'] for r in results if r['weekly_p99'] == max(weekly_p99s)][0]})")
    
    print(f"\n💡 数据说明:")
    print(f"  • 基于 2025年8月3日-9日 真实数据")
    print(f"  • avg: 每日平均论文数")
    print(f"  • max: 7天内单日最高论文数")
    print(f"  • p99: 99百分位数（排除最高1%的极端值）")
    print(f"  • 30天估算 = 7天实际数据 × 4.3")


def main():
    print("🚀 arXiv cs分类论文统计报告")
    print("基于最近7天实际数据的30天估算分析\n")
    
    print_comprehensive_monthly_report()
    
    print(f"\n⏱️  报告生成完成")


if __name__ == "__main__":
    main()