"""
Data Management Utilities

封装数据存储和读取功能
"""

import pandas as pd
import datetime
from pathlib import Path
from typing import Set, Dict, Optional, List
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger


class PaperMetaManager:
    """论文元数据管理器"""
    
    def __init__(self, meta_file: str):
        """
        初始化管理器
        
        Args:
            meta_file: 元数据文件路径
        """
        self.meta_file = meta_file
        self.df = self._load_data()
    
    def _load_data(self) -> pd.DataFrame:
        """加载数据"""
        Path("data").mkdir(exist_ok=True)
        
        if not Path(self.meta_file).exists():
            logger.info(f"文件不存在: {self.meta_file}, creating default empty dataframe")
            dict_keys = ArxivPaper.model_fields.keys()
            return pd.DataFrame(columns=dict_keys)
        
        try:
            df = pd.read_parquet(self.meta_file)
            logger.info(f"从{self.meta_file}加载了{len(df)}篇论文")
            return df
        except Exception as e:
            logger.error(f"Error loading {self.meta_file}: {str(e)}")
            raise e
    
    def filter_new_papers(self, papers: dict[str, ArxivPaper]) -> dict[str, ArxivPaper]:
        """
        过滤出新论文（未存在于数据库中的论文）
        
        Args:
            papers: 论文字典
            
        Returns:
            过滤后的新论文字典
        """
        existing_ids = set(self.df["paper_id"].tolist())
        new_papers = {k: v for k, v in papers.items() if v.paper_id not in existing_ids}
        logger.info(f"过滤出{len(new_papers)}篇新论文（原有{len(papers)}篇）")
        return new_papers
    
    def get_paper(self, paper_ids: list[str]) -> list[Optional[ArxivPaper]]:
        """
        获取指定ID的论文
        
        Args:
            paper_ids: 论文ID列表
            
        Returns:
            论文数据Series，如果不存在则返回None
        """
        matches = self.df[self.df["paper_id"].isin(paper_ids)]
        if matches.empty:
            return [None] * len(paper_ids)
        
        return matches.to_dict(orient="records")
    
    def set_paper(self, papers: list[ArxivPaper]) -> None:
        """
        设置/更新论文数据
        
        Args:
            papers: 论文对象列表
        """
        # 将ArxivPaper对象转换为字典
        paper_dict = [paper.model_dump() for paper in papers]
        new_df = pd.DataFrame(paper_dict)
        
        self.df = pd.concat([self.df, new_df], ignore_index=False)
        self.df = self.df[~self.df.index.duplicated(keep="last")]
    
    def persist(self) -> None:
        """持久化数据到文件"""
        if not self.df.empty:
            self.df.to_parquet(self.meta_file, engine="pyarrow")
            logger.info(f"持久化了{len(self.df)}篇论文到{self.meta_file}")
    
    def get_paper_by_day(self, target_date: datetime.date = None) -> pd.DataFrame:
        """
        获取指定日期的论文
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            筛选后的DataFrame
        """
        target_date = target_date or datetime.date.today()
        if self.df.empty:
            return pd.DataFrame()
        
        daily_papers = self.df[self.df["update_time"] == target_date]
        logger.info(f"找到{len(daily_papers)}篇{target_date}的论文")
        return daily_papers
    
    def update_paper_summaries(self, summaries: dict[str, str]) -> None:
        """
        更新论文摘要
        
        Args:
            summaries: 摘要字典，key为paper_id
        """
        if not summaries:
            return
        
        # 方法1：使用pandas的map函数批量更新
        # 创建一个Series用于映射
        summary_series = pd.Series(summaries)
        
        # 找到需要更新的行
        mask = self.df["paper_id"].isin(summaries.keys())
        
        # 批量更新
        if mask.any():
            # 使用map函数批量更新
            self.df.loc[mask, "summary"] = self.df.loc[mask, "paper_id"].map(summary_series)
            
            updated_count = mask.sum()
            logger.info(f"更新了{updated_count}篇论文的摘要")

    def update_push_status(self, paper_ids: list[str]) -> None:
        """
        更新推送状态
        
        Args:
            paper_ids: 已推送的论文ID列表
        """
        if not paper_ids:
            return
        
        # 方法2：使用isin + loc的组合进行批量更新
        # 找到需要更新的行
        mask = self.df["paper_id"].isin(paper_ids)
        
        if mask.any():
            # 批量更新推送状态
            self.df.loc[mask, "pushed"] = True
            
            updated_count = mask.sum()
            logger.info(f"更新了{updated_count}篇论文的推送状态")
    
    # 新增：批量更新多个字段的方法
    def update_papers_batch(self, updates: dict[str, dict]) -> None:
        """
        批量更新论文的多个字段
        
        Args:
            updates: 更新字典，格式为 {paper_id: {field: value, ...}}
        """
        if not updates:
            return
        
        # 创建更新DataFrame
        update_df = pd.DataFrame.from_dict(updates, orient='index')
        update_df.index.name = 'paper_id'
        update_df = update_df.reset_index()
        
        # 找到需要更新的行
        mask = self.df["paper_id"].isin(updates.keys())
        
        if mask.any():
            # 使用merge进行批量更新
            # 为每个字段批量更新
            for field in update_df.columns:
                if field == 'paper_id':
                    continue
                    
                # 创建映射字典
                field_mapping = dict(zip(update_df['paper_id'], update_df[field]))
                
                # 批量更新
                self.df.loc[mask, field] = self.df.loc[mask, 'paper_id'].map(field_mapping)
            
            updated_count = mask.sum()
            logger.info(f"批量更新了{updated_count}篇论文的{len(update_df.columns)-1}个字段")
    
    def get_all_papers(self) -> pd.DataFrame:
        """获取所有论文"""
        return self.df.copy()
    
    def get_paper_count(self) -> int:
        """获取论文总数"""
        return len(self.df)


if __name__ == "__main__":
    # 测试PaperMetaManager
    test_paper = ArxivPaper(
        paper_id="test123",
        paper_title="Test Paper",
        paper_url="https://arxiv.org/abs/test123",
        paper_abstract="This is a test paper",
        paper_authors="Test Author",
        paper_first_author="Test Author",
        primary_category="cs.AI",
        publish_time=datetime.date.today(),
        update_time=datetime.date.today(),
        comments=None,
    )
    
    # 测试PaperMetaManager
    test_file = "data/test_papers.parquet"
    manager = PaperMetaManager(test_file)
    
    # 测试设置论文
    manager.set_paper([test_paper])
    manager.persist()
    
    # 测试获取论文
    papers = manager.get_paper(["test123"])
    print(f"获取论文: {papers[0]['paper_title'] if papers[0] is not None else 'None'}")
    
    # 测试按日期获取
    daily_papers = manager.get_paper_by_day(datetime.date.today())
    print(f"今日论文数量: {len(daily_papers)}")
    
    # 清理测试文件
    import os
    if os.path.exists(test_file):
        os.remove(test_file)
        print("清理测试文件完成")
