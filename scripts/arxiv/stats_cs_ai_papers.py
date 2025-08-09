#!/usr/bin/env python3
"""
统计arXiv cs分类最近N天的论文数量

支持多种cs分类，提供详细统计信息
"""

import datetime
from typing import Dict, List, NamedTuple
import argparse
import csv
import logging
import sys
import statistics

import arxiv

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 支持的cs分类
CS_CATEGORIES = {
    'cs.AI': 'Artificial Intelligence',
    'cs.IR': 'Information Retrieval',
    'cs.CL': 'Computation and Language',
    'cs.CV': 'Computer Vision and Pattern Recognition',
    'cs.LG': 'Machine Learning',
    'cs.DB': 'Databases',
    'cs.DC': 'Distributed, Parallel, and Cluster Computing',
    'cs.DS': 'Data Structures and Algorithms',
    'cs.HC': 'Human-Computer Interaction',
    'cs.NE': 'Neural and Evolutionary Computing',
    'cs.RO': 'Robotics',
    'cs.SE': 'Software Engineering',
    'cs.SY': 'Systems and Control',
    'cs.CR': 'Cryptography and Security',
    'cs.GT': 'Computer Science and Game Theory',
    'cs.NI': 'Networking and Internet Architecture',
    'cs.OS': 'Operating Systems',
    'cs.PL': 'Programming Languages',
}


class PaperInfo(NamedTuple):
    """论文信息"""
    paper_id: str
    title: str
    authors: str
    abstract: str
    published: datetime.date
    updated: datetime.date
    url: str


def format_date_chinese(date: datetime.date) -> str:
    """格式化日期为中文显示"""
    return f"{date.year}年{date.month}月{date.day}日"


def get_papers_by_date_range(category: str = 'cs.AI', days: int = 7, max_results: int = 1000) -> Dict[str, List[PaperInfo]]:
    """
    获取指定cs分类下指定天数内的论文，按日期分组
    
    Args:
        category: cs分类，如cs.AI, cs.IR等
        days: 获取最近几天的论文，默认7天
        max_results: 最大结果数量，默认1000
        
    Returns:
        以日期为key，论文列表为value的字典
    """
    if category not in CS_CATEGORIES:
        raise ValueError(f"不支持的分类: {category}。支持的分类: {', '.join(CS_CATEGORIES.keys())}")
        
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)  # 最近days天（包括今天）
    
    category_name = CS_CATEGORIES[category]
    logger.info(f"获取 {category} ({category_name}) 分类论文，时间范围: {format_date_chinese(start_date)} 至 {format_date_chinese(end_date)}")
    
    # 构建arXiv搜索查询语句
    query = f'cat:{category}'
    
    # 创建搜索对象
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    logger.info(f"开始从arXiv获取论文...")
    
    # 按日期分组
    papers_by_date = {}
    total_papers = 0
    
    try:
        for result in search.results():
            # 获取论文信息
            paper_id = result.get_short_id()
            title = result.title
            authors = ', '.join([author.name for author in result.authors])
            abstract = result.summary.replace('\n', ' ')
            published = result.published.date()
            updated = result.updated.date()
            url = result.entry_id
            
            # 使用论文的更新时间作为分组依据
            paper_date = updated
            
            # 只统计指定日期范围内的论文
            if start_date <= paper_date <= end_date:
                date_str = paper_date.strftime('%Y-%m-%d')
                if date_str not in papers_by_date:
                    papers_by_date[date_str] = []
                
                paper_info = PaperInfo(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    published=published,
                    updated=updated,
                    url=url
                )
                
                papers_by_date[date_str].append(paper_info)
                total_papers += 1
                
                logger.debug(f"论文 {paper_id} ({paper_date}) 已添加到统计")
            else:
                logger.debug(f"论文 {paper_id} 日期 {paper_date} 不在统计范围内")
    except arxiv.UnexpectedEmptyPageError as e:
        logger.warning(f"arXiv API返回空页面，可能已获取所有可用论文: {e}")
    except Exception as e:
        logger.error(f"从arXiv获取论文时发生错误: {e}")
        # 继续处理已经获取到的论文
    
    logger.info(f"从arXiv获取到 {total_papers} 篇在统计范围内的论文")
    return papers_by_date


def calculate_daily_stats(papers_by_date: Dict[str, List[PaperInfo]], days: int) -> Dict[str, float]:
    """
    计算每日论文数量的详细统计信息
    
    Args:
        papers_by_date: 按日期分组的论文字典
        days: 统计天数
        
    Returns:
        统计信息字典，包含avg, p99, max等
    """
    # 收集每天的论文数量（包括0篇的日期）
    daily_counts = []
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        count = len(papers_by_date.get(date_str, []))
        daily_counts.append(count)
        current_date += datetime.timedelta(days=1)
    
    stats = {}
    if daily_counts:
        stats['total'] = sum(daily_counts)
        stats['avg'] = statistics.mean(daily_counts)
        stats['median'] = statistics.median(daily_counts)
        stats['max'] = max(daily_counts)
        stats['min'] = min(daily_counts)
        
        # 计算p99 (99th percentile)
        sorted_counts = sorted(daily_counts)
        if len(sorted_counts) > 1:
            p99_index = int(0.99 * (len(sorted_counts) - 1))
            stats['p99'] = sorted_counts[p99_index]
        else:
            stats['p99'] = sorted_counts[0] if sorted_counts else 0
            
        # 标准差
        if len(daily_counts) > 1:
            stats['std'] = statistics.stdev(daily_counts)
        else:
            stats['std'] = 0.0
            
        # 活跃日期统计
        active_days = [count for count in daily_counts if count > 0]
        stats['active_days'] = len(active_days)
        stats['active_avg'] = statistics.mean(active_days) if active_days else 0.0
    
    return stats


def print_statistics(papers_by_date: Dict[str, List[PaperInfo]], days: int, category: str = 'cs.AI'):
    """
    打印统计信息
    
    Args:
        papers_by_date: 按日期分组的论文字典
        days: 统计天数
        category: 分类名称
    """
    category_name = CS_CATEGORIES.get(category, category)
    stats = calculate_daily_stats(papers_by_date, days)
    
    print(f"\n📊 arXiv {category} ({category_name}) 最近 {days} 天论文统计")
    print("=" * 60)
    
    # 按日期排序显示每日详情
    sorted_dates = sorted(papers_by_date.keys(), reverse=True)
    
    print("📅 每日论文数量:")
    for date_str in sorted_dates:
        papers = papers_by_date[date_str]
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        chinese_date = format_date_chinese(date_obj)
        
        print(f"  {chinese_date} ({date_str}): {len(papers)} 篇")
        
        if len(papers) > 0:
            # 显示论文标题（最多显示2篇）
            for i, paper in enumerate(papers[:2]):
                title = paper.title[:50] + '...' if len(paper.title) > 50 else paper.title
                print(f"    - {title}")
            
            if len(papers) > 2:
                print(f"    ... 还有 {len(papers) - 2} 篇论文")
    
    # 统计没有论文的日期
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)
    current_date = start_date
    missing_dates = []
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in papers_by_date:
            missing_dates.append(date_str)
        current_date += datetime.timedelta(days=1)
    
    if missing_dates and len(missing_dates) < days:
        print(f"\n📭 无论文的日期 ({len(missing_dates)} 天):")
        for date_str in missing_dates:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            chinese_date = format_date_chinese(date_obj)
            print(f"  {chinese_date} ({date_str})")
    
    # 详细统计信息
    print(f"\n📈 详细统计信息:")
    print(f"  总计论文数: {stats['total']} 篇")
    print(f"  平均每天: {stats['avg']:.1f} 篇")
    print(f"  中位数: {stats['median']:.1f} 篇")
    print(f"  最大值: {stats['max']} 篇")
    print(f"  最小值: {stats['min']} 篇")
    print(f"  P99: {stats['p99']} 篇")
    print(f"  标准差: {stats['std']:.1f}")
    print(f"  活跃日期: {stats['active_days']}/{days} 天")
    if stats['active_days'] > 0:
        print(f"  活跃日期平均: {stats['active_avg']:.1f} 篇")


def export_to_csv(papers_by_date: Dict[str, List[PaperInfo]], filename: str):
    """
    导出统计数据到CSV文件
    
    Args:
        papers_by_date: 按日期分组的论文字典
        filename: 输出文件名
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['date', 'paper_count', 'paper_ids', 'paper_titles', 'authors', 'urls']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        sorted_dates = sorted(papers_by_date.keys(), reverse=True)
        for date_str in sorted_dates:
            papers = papers_by_date[date_str]
            paper_ids = '; '.join([paper.paper_id for paper in papers])
            paper_titles = '; '.join([paper.title for paper in papers])
            authors = '; '.join([paper.authors for paper in papers])
            urls = '; '.join([paper.url for paper in papers])
            
            writer.writerow({
                'date': date_str,
                'paper_count': len(papers),
                'paper_ids': paper_ids,
                'paper_titles': paper_titles,
                'authors': authors,
                'urls': urls
            })
    
    logger.info(f"统计数据已导出到: {filename}")


def list_categories():
    """列出所有支持的分类"""
    print("\n📚 支持的arXiv cs分类:")
    print("=" * 50)
    for category, name in CS_CATEGORIES.items():
        print(f"  {category:<8} - {name}")
    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='统计arXiv cs分类最近N天的论文数量',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/stats_cs_ai_papers.py                          # 统计cs.AI最近7天
  python scripts/stats_cs_ai_papers.py --category cs.IR         # 统计cs.IR分类
  python scripts/stats_cs_ai_papers.py --days 14 --category cs.CV  # 统计cs.CV最近14天  
  python scripts/stats_cs_ai_papers.py --list-categories         # 列出所有支持的分类
  python scripts/stats_cs_ai_papers.py --export stats.csv       # 统计并导出到CSV文件
        """
    )
    
    parser.add_argument(
        '--category',
        type=str,
        default='cs.AI',
        help='要统计的cs分类，默认cs.AI'
    )
    
    parser.add_argument(
        '--days', 
        type=int, 
        default=7, 
        help='统计最近几天的论文，默认7天'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        default=1000,
        help='从arXiv获取的最大论文数量，默认1000'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        help='导出统计数据到CSV文件'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志信息'
    )
    
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='列出所有支持的分类并退出'
    )
    
    args = parser.parse_args()
    
    # 如果只是列出分类，直接返回
    if args.list_categories:
        list_categories()
        return
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # 获取论文数据
        papers_by_date = get_papers_by_date_range(args.category, args.days, args.max_results)
        
        # 打印统计信息
        print_statistics(papers_by_date, args.days, args.category)
        
        # 如果指定了导出选项，导出到CSV
        if args.export:
            export_to_csv(papers_by_date, args.export)
    
    except Exception as e:
        logger.error(f"统计过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()