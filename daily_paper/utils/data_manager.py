"""
Data Management Utilities

封装数据存储和读取功能
"""

import pandas as pd
import datetime
import logging
from pathlib import Path
from typing import Dict, Set
from .arxiv_client import ArxivPaper

def save_papers_to_parquet(papers: Dict[str, ArxivPaper], meta_file: str) -> None:
    """
    保存论文数据到parquet文件
    
    Args:
        papers: 论文字典
        meta_file: 元数据文件路径
    """
    Path("data").mkdir(exist_ok=True)
    
    # 读取已有数据
    existing_df = pd.DataFrame()
    if Path(meta_file).exists():
        try:
            existing_df = pd.read_parquet(meta_file)
        except Exception as e:
            logging.warning(f"Error reading existing file: {str(e)}")
    
    # 合并新旧数据时添加必要字段
    new_df = pd.DataFrame.from_dict(papers, orient='index')
    if not new_df.empty:
        new_df['summary'] = None
        new_df['pushed'] = False
    
    # 合并数据
    if existing_df.empty:
        combined_df = new_df
    else:
        combined_df = pd.concat([existing_df, new_df], ignore_index=False)
    
    # 去重并保存
    if not combined_df.empty:
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        combined_df.to_parquet(meta_file, engine='pyarrow')
        logging.info(f"保存了{len(papers)}篇新论文到{meta_file}")

def load_papers_from_parquet(meta_file: str) -> pd.DataFrame:
    """
    从parquet文件加载论文数据
    
    Args:
        meta_file: 元数据文件路径
        
    Returns:
        论文数据DataFrame
    """
    if not Path(meta_file).exists():
        logging.info(f"文件不存在: {meta_file}")
        return pd.DataFrame()
    
    try:
        df = pd.read_parquet(meta_file)
        logging.info(f"从{meta_file}加载了{len(df)}篇论文")
        return df
    except Exception as e:
        logging.error(f"Error loading {meta_file}: {str(e)}")
        return pd.DataFrame()

def get_existing_paper_ids(meta_file: str) -> Set[str]:
    """
    获取已存在的论文ID集合
    
    Args:
        meta_file: 元数据文件路径
        
    Returns:
        已存在的论文ID集合
    """
    existing_ids = set()
    
    if Path(meta_file).exists():
        try:
            df = pd.read_parquet(meta_file)
            if not df.empty and 'paper_id' in df.columns:
                existing_ids.update(df['paper_id'].tolist())
        except Exception as e:
            logging.warning(f"Error reading {meta_file}: {str(e)}")
    
    return existing_ids

def filter_new_papers(papers: Dict[str, ArxivPaper], meta_file: str) -> Dict[str, ArxivPaper]:
    """
    过滤出新论文（未存在于数据库中的论文）
    
    Args:
        papers: 论文字典
        meta_file: 元数据文件路径
        
    Returns:
        过滤后的新论文字典
    """
    existing_ids = get_existing_paper_ids(meta_file)
    new_papers = {k: v for k, v in papers.items() if v['paper_id'] not in existing_ids}
    
    logging.info(f"过滤出{len(new_papers)}篇新论文（原有{len(papers)}篇）")
    return new_papers

def update_paper_summaries(df: pd.DataFrame, summaries: Dict[str, str]) -> pd.DataFrame:
    """
    更新论文摘要
    
    Args:
        df: 论文数据DataFrame
        summaries: 摘要字典，key为DataFrame的index
        
    Returns:
        更新后的DataFrame
    """
    # 添加缺失的summary列
    if 'summary' not in df.columns:
        df['summary'] = None
    
    # 批量更新摘要
    for index, summary in summaries.items():
        if index in df.index:
            df.at[index, 'summary'] = summary
    
    logging.info(f"更新了{len(summaries)}篇论文的摘要")
    return df

def update_push_status(df: pd.DataFrame, pushed_indices: list, meta_file: str) -> pd.DataFrame:
    """
    更新推送状态
    
    Args:
        df: 论文数据DataFrame
        pushed_indices: 已推送的索引列表
        meta_file: 元数据文件路径
        
    Returns:
        更新后的DataFrame
    """
    if pushed_indices:
        df.loc[pushed_indices, 'pushed'] = True
        df.to_parquet(meta_file, engine='pyarrow')
        logging.info(f"成功更新{len(pushed_indices)}篇论文推送状态")
    
    return df

def get_unpushed_papers_with_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    获取有摘要但未推送的论文
    
    Args:
        df: 论文数据DataFrame
        
    Returns:
        筛选后的DataFrame
    """
    # 确保必要的列存在
    if 'pushed' not in df.columns:
        df['pushed'] = False
    if 'summary' not in df.columns:
        df['summary'] = None
    
    # 筛选需要推送的论文
    to_push = df[(df['pushed'] == False) & (df['summary'].notna())].copy()
    
    logging.info(f"找到{len(to_push)}篇需要推送的论文")
    return to_push

def get_papers_without_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    获取没有摘要的论文
    
    Args:
        df: 论文数据DataFrame
        
    Returns:
        筛选后的DataFrame
    """
    # 添加缺失的summary列
    if 'summary' not in df.columns:
        df['summary'] = None

    # 过滤掉已经有summary的论文
    papers_without_summary = df[df['summary'].isna()]
    
    logging.info(f"找到{len(papers_without_summary)}篇需要生成摘要的论文")
    return papers_without_summary

def get_daily_papers(df: pd.DataFrame, target_date: datetime.date = None) -> pd.DataFrame:
    """
    获取指定日期的论文
    
    Args:
        df: 论文数据DataFrame
        target_date: 目标日期，默认为今天
        
    Returns:
        筛选后的DataFrame
    """
    target_date = target_date or datetime.date.today()
    daily_papers = df[df['update_time'] == target_date]
    
    logging.info(f"找到{len(daily_papers)}篇{target_date}的论文")
    return daily_papers

def reset_push_status(df: pd.DataFrame, days: int, meta_file: str) -> pd.DataFrame:
    """
    重置最近几天的推送状态
    
    Args:
        df: 论文数据DataFrame
        days: 天数
        meta_file: 元数据文件路径
        
    Returns:
        更新后的DataFrame
    """
    # 计算日期范围
    cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
    
    # 筛选需要重置的记录
    mask = df['update_time'] >= cutoff_date
    reset_count = df.loc[mask, 'pushed'].sum()
    
    # 执行状态重置
    df.loc[mask, 'pushed'] = False
    
    # 保存更新到文件
    df.to_parquet(meta_file, engine='pyarrow')
    logging.info(f"已重置最近{days}天内{reset_count}篇论文的推送状态")
    return df

if __name__ == "__main__":
    # 测试函数
    test_papers = {
        "test123": ArxivPaper(
            paper_id="test123",
            paper_title="Test Paper",
            paper_url="https://arxiv.org/abs/test123",
            paper_abstract="This is a test paper",
            paper_authors="Test Author",
            paper_first_author="Test Author",
            primary_category="cs.AI",
            publish_time=datetime.date.today(),
            update_time=datetime.date.today(),
            comments=None
        )
    }
    
    # 测试保存和加载
    test_file = "data/test_papers.parquet"
    save_papers_to_parquet(test_papers, test_file)
    
    df = load_papers_from_parquet(test_file)
    print(f"加载了{len(df)}篇论文")
    
    # 清理测试文件
    import os
    if os.path.exists(test_file):
        os.remove(test_file) 