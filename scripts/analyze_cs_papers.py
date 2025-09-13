#!/usr/bin/env python3
"""
分析CS论文统计数据
读取parquet文件并生成详细的统计报告
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import os

def analyze_cs_papers(parquet_file):
    """分析CS论文数据"""
    print(f"📖 Reading data from: {parquet_file}")
    
    # 读取数据
    df = pd.read_csv if parquet_file.endswith('.csv') else pd.read_parquet
    data = df(parquet_file)
    
    print(f"📊 Total papers loaded: {len(data):,}")
    print("="*60)
    
    # 基本统计
    print("📅 Time Range Analysis")
    print("-" * 30)
    if 'date_submitted' in data.columns:
        data['date_submitted'] = pd.to_datetime(data['date_submitted'])
        print(f"Date range: {data['date_submitted'].min().date()} to {data['date_submitted'].max().date()}")
        
        # 按月统计
        monthly = data.groupby(data['date_submitted'].dt.to_period('M')).size()
        print(f"\n📈 Papers by Month:")
        for month, count in monthly.items():
            print(f"   {month}: {count:,}")
    
    print("\n" + "="*60)
    
    # CS分类统计
    print("🏷️  CS Categories Analysis")
    print("-" * 30)
    
    if 'cs_categories' in data.columns:
        # 展开所有分类
        all_categories = []
        for cats in data['cs_categories'].dropna():
            # 处理分类字符串，移除重复的"cs:"前缀
            categories = cats.split('; ')
            clean_cats = []
            for cat in categories:
                if cat.startswith('cs:cs:'):
                    clean_cats.append(cat.replace('cs:cs:', 'cs.'))
                elif cat.startswith('cs:'):
                    clean_cats.append(cat.replace('cs:', 'cs.'))
                else:
                    clean_cats.append(cat)
            all_categories.extend(clean_cats)
        
        cat_counts = Counter(all_categories)
        
        print(f"📊 All CS Categories ({len(cat_counts)} total):")
        print(f"Top 20:")
        for i, (cat, count) in enumerate(cat_counts.most_common(20), 1):
            percentage = (count / len(data)) * 100
            print(f"   {i:2d}. {cat:<6}: {count:>6,} ({percentage:5.1f}%)")
        
        # 主要分类详细统计
        major_categories = {cat: count for cat, count in cat_counts.items() if count >= 1000}
        
        print(f"\n🎯 Major Categories (≥1000 papers, {len(major_categories)} categories):")
        total_major = sum(major_categories.values())
        for i, (cat, count) in enumerate(sorted(major_categories.items(), key=lambda x: x[1], reverse=True), 1):
            percentage = (count / len(data)) * 100
            major_pct = (count / total_major) * 100
            print(f"   {i:2d}. {cat:<6}: {count:>6,} ({percentage:5.1f}% of all, {major_pct:5.1f}% of major)")
    
    print("\n" + "="*60)
    
    # 按分类的月度趋势
    if 'cs_categories' in data.columns and 'date_submitted' in data.columns:
        print("📈 Monthly Trends for Top Categories")
        print("-" * 30)
        
        # 获取前10大分类
        top_10_cats = [cat for cat, _ in cat_counts.most_common(10)]
        
        # 为每个分类创建月度统计
        monthly_by_cat = {}
        for cat in top_10_cats:
            # 筛选包含该分类的论文
            mask = data['cs_categories'].str.contains(cat.replace('cs.', 'cs:'), na=False)
            cat_data = data[mask]
            if len(cat_data) > 0:
                monthly_cat = cat_data.groupby(cat_data['date_submitted'].dt.to_period('M')).size()
                monthly_by_cat[cat] = monthly_cat
        
        # 显示每个分类的月度趋势
        all_months = sorted(set().union(*[m.index for m in monthly_by_cat.values()]))
        
        print(f"\nMonthly breakdown for top categories:")
        print(f"{'Category':<8} " + " ".join(f"{m}"[-7:] for m in all_months))
        print("-" * (8 + len(all_months) * 8))
        
        for cat in top_10_cats[:10]:  # 限制显示前10个
            if cat in monthly_by_cat:
                monthly = monthly_by_cat[cat]
                row = f"{cat:<8} "
                for month in all_months:
                    count = monthly.get(month, 0)
                    row += f"{count:>7} "
                print(row)
    
    print("\n" + "="*60)
    
    # 论文长度统计
    print("📝 Content Analysis")
    print("-" * 30)
    
    if 'title' in data.columns:
        titles = data['title'].dropna()
        title_lengths = titles.str.len()
        print(f"📋 Title Statistics:")
        print(f"   Average length: {title_lengths.mean():.1f} characters")
        print(f"   Median length:  {title_lengths.median():.1f} characters")
        print(f"   Max length:     {title_lengths.max()} characters")
        print(f"   Min length:     {title_lengths.min()} characters")
    
    if 'abstract' in data.columns:
        abstracts = data['abstract'].dropna()
        abstract_lengths = abstracts.str.len()
        print(f"\n📄 Abstract Statistics:")
        print(f"   Average length: {abstract_lengths.mean():.0f} characters")
        print(f"   Median length:  {abstract_lengths.median():.0f} characters")
        print(f"   Max length:     {abstract_lengths.max():,} characters")
        print(f"   Min length:     {abstract_lengths.min()} characters")
    
    if 'authors' in data.columns:
        authors = data['authors'].dropna()
        author_counts = authors.str.count(';') + 1  # 分号分隔的作者数
        print(f"\n👥 Author Statistics:")
        print(f"   Average authors per paper: {author_counts.mean():.1f}")
        print(f"   Median authors per paper:  {author_counts.median():.1f}")
        print(f"   Max authors per paper:     {author_counts.max()}")
        print(f"   Single author papers:      {(author_counts == 1).sum():,} ({(author_counts == 1).mean()*100:.1f}%)")
    
    print("\n" + "="*60)
    print("✅ Analysis completed!")
    
    return data, cat_counts

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="分析CS论文统计数据")
    parser.add_argument("--file", 
                        default="arxiv_data/cs_papers_6months_20250811_222915.parquet",
                        help="Parquet文件路径")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        # 尝试寻找其他parquet文件
        data_dir = os.path.dirname(args.file) or "arxiv_data"
        if os.path.exists(data_dir):
            parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet') and 'cs_papers' in f]
            if parquet_files:
                latest_file = sorted(parquet_files)[-1]
                args.file = os.path.join(data_dir, latest_file)
                print(f"🔍 Found alternative file: {args.file}")
            else:
                print(f"❌ No suitable parquet files found in {data_dir}")
                return 1
        else:
            return 1
    
    try:
        data, cat_counts = analyze_cs_papers(args.file)
        
        # 保存分类统计到CSV
        output_dir = os.path.dirname(args.file)
        stats_file = os.path.join(output_dir, "cs_categories_stats.csv")
        
        stats_df = pd.DataFrame([
            {'category': cat, 'count': count, 'percentage': (count/len(data))*100}
            for cat, count in cat_counts.most_common()
        ])
        stats_df.to_csv(stats_file, index=False)
        print(f"📊 Category statistics saved to: {stats_file}")
        
    except Exception as e:
        print(f"❌ Error analyzing data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())