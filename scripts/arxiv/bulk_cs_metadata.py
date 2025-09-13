#!/usr/bin/env python3
"""
批量获取arXiv CS领域最近6个月所有论文的metadata并保存为parquet格式

使用OAI-PMH协议高效获取大量元数据，避免API频率限制
支持断点续传和增量更新
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from urllib.parse import urlencode

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_cs_metadata.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CS分类列表 - 包含所有CS子领域
CS_CATEGORIES = {
    'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV', 
    'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
    'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
    'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS',
    'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY'
}

# OAI-PMH命名空间
NAMESPACES = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'arXiv': 'http://arxiv.org/OAI/arXiv/'
}

class ArxivBulkFetcher:
    """arXiv批量元数据获取器"""
    
    def __init__(self, output_dir: str = "arxiv_data", months_back: int = 6):
        self.base_url = "http://export.arxiv.org/oai2"
        self.output_dir = output_dir
        self.months_back = months_back
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivBulkFetcher/1.0 (Research Tool)'
        })
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 用于跟踪处理进度的文件
        self.progress_file = os.path.join(self.output_dir, "progress.txt")
        self.checkpoint_file = os.path.join(self.output_dir, "checkpoint.txt")
        
    def get_date_range(self) -> tuple:
        """获取日期范围"""
        # arXiv数据通常有1-2天延迟，所以结束日期设为昨天
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=self.months_back * 30)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def load_checkpoint(self) -> Optional[str]:
        """加载断点续传信息"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return f.read().strip()
        return None
    
    def save_checkpoint(self, resumption_token: str):
        """保存断点续传信息"""
        with open(self.checkpoint_file, 'w') as f:
            f.write(resumption_token)
    
    def clear_checkpoint(self):
        """清除断点续传信息"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
    
    def make_oai_request(self, verb: str, params: Dict[str, str]) -> ET.Element:
        """发起OAI-PMH请求"""
        params['verb'] = verb
        url = f"{self.base_url}?{urlencode(params)}"
        
        logger.debug(f"OAI request: {url}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # 解析XML响应
                root = ET.fromstring(response.content)
                
                # 检查是否有错误
                error = root.find('.//oai:error', NAMESPACES)
                if error is not None:
                    error_code = error.get('code', 'unknown')
                    error_msg = error.text or 'Unknown error'
                    raise Exception(f"OAI error {error_code}: {error_msg}")
                
                return root
                
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
    
    def extract_metadata_from_record(self, record: ET.Element) -> Optional[Dict]:
        """从OAI记录中提取元数据"""
        try:
            header = record.find('oai:header', NAMESPACES)
            if header is None:
                return None
            
            # 检查是否被删除
            if header.get('status') == 'deleted':
                return None
                
            # 获取基本信息
            identifier = header.find('oai:identifier', NAMESPACES)
            datestamp = header.find('oai:datestamp', NAMESPACES)
            
            if identifier is None or datestamp is None:
                return None
            
            arxiv_id = identifier.text.replace('oai:arXiv.org:', '')
            
            # 获取分类信息
            set_specs = header.findall('oai:setSpec', NAMESPACES)
            categories = [spec.text for spec in set_specs if spec.text]
            
            # 过滤CS分类
            cs_categories = [cat for cat in categories if cat.startswith('cs')]
            if not cs_categories:
                return None
            
            # 获取详细元数据
            metadata = record.find('.//oai_dc:dc', NAMESPACES)
            if metadata is None:
                return None
            
            # 提取各字段
            def get_text_list(element_name):
                elements = metadata.findall(f'dc:{element_name}', NAMESPACES)
                return [elem.text for elem in elements if elem.text]
            
            def get_text_first(element_name):
                elements = get_text_list(element_name)
                return elements[0] if elements else None
            
            paper_data = {
                'arxiv_id': arxiv_id,
                'title': get_text_first('title'),
                'authors': '; '.join(get_text_list('creator')),
                'abstract': get_text_first('description'),
                'subject_categories': '; '.join(categories),
                'cs_categories': '; '.join(cs_categories),
                'date_submitted': datestamp.text,
                'last_updated': datestamp.text,
                'doi': get_text_first('relation'),
                'journal_ref': get_text_first('source'),
                'fetch_time': datetime.now().isoformat()
            }
            
            # 验证必要字段
            if not paper_data['title'] or not paper_data['authors']:
                logger.debug(f"Skipping paper {arxiv_id} due to missing title/authors")
                return None
                
            return paper_data
            
        except Exception as e:
            logger.warning(f"Error extracting metadata from record: {e}")
            return None
    
    def fetch_cs_papers_batch(self, resumption_token: Optional[str] = None) -> List[Dict]:
        """批量获取CS论文元数据"""
        papers = []
        
        if resumption_token:
            params = {'resumptionToken': resumption_token}
            logger.info(f"Resuming from token: {resumption_token[:50]}...")
        else:
            # 设置日期范围
            start_date, end_date = self.get_date_range()
            logger.info(f"Fetching CS papers from {start_date} to {end_date}")
            
            params = {
                'metadataPrefix': 'oai_dc',
                'set': 'cs',  # CS分类
                'from': start_date,
                'until': end_date
            }
        
        try:
            root = self.make_oai_request('ListRecords', params)
            
            # 解析记录
            records = root.findall('.//oai:record', NAMESPACES)
            logger.info(f"Processing {len(records)} records in this batch")
            
            for record in records:
                paper_data = self.extract_metadata_from_record(record)
                if paper_data:
                    papers.append(paper_data)
            
            # 检查是否有更多数据
            resumption_token_elem = root.find('.//oai:resumptionToken', NAMESPACES)
            next_token = resumption_token_elem.text if resumption_token_elem is not None else None
            
            logger.info(f"Extracted {len(papers)} valid CS papers from this batch")
            
            return papers, next_token
            
        except Exception as e:
            logger.error(f"Error fetching batch: {e}")
            return [], None
    
    def fetch_all_cs_papers(self, max_papers: Optional[int] = None) -> List[Dict]:
        """获取所有CS论文元数据"""
        all_papers = []
        processed_count = 0
        batch_count = 0
        
        # 检查是否有断点续传
        resumption_token = self.load_checkpoint()
        if resumption_token:
            logger.info("Found checkpoint, resuming from previous session")
        
        start_time = time.time()
        
        try:
            while True:
                batch_count += 1
                logger.info(f"Processing batch {batch_count}...")
                
                papers, next_token = self.fetch_cs_papers_batch(resumption_token)
                
                if not papers:
                    logger.info("No more papers to fetch")
                    break
                
                all_papers.extend(papers)
                processed_count += len(papers)
                
                # 保存中间结果
                if batch_count % 10 == 0:  # 每10个batch保存一次
                    self.save_intermediate_results(all_papers, batch_count)
                
                logger.info(f"Total papers collected: {processed_count}")
                
                # 检查是否达到最大数量限制
                if max_papers and processed_count >= max_papers:
                    logger.info(f"Reached maximum paper limit: {max_papers}")
                    break
                
                # 保存断点
                if next_token:
                    self.save_checkpoint(next_token)
                    resumption_token = next_token
                    
                    # 遵守API速率限制
                    time.sleep(1)
                else:
                    logger.info("Reached end of results")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Process interrupted by user")
        except Exception as e:
            logger.error(f"Error during bulk fetch: {e}")
        finally:
            # 清理断点文件
            self.clear_checkpoint()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Fetch completed. Total time: {elapsed_time:.2f}s, Total papers: {len(all_papers)}")
        
        return all_papers
    
    def save_intermediate_results(self, papers: List[Dict], batch_num: int):
        """保存中间结果"""
        if not papers:
            return
            
        intermediate_file = os.path.join(self.output_dir, f"intermediate_batch_{batch_num}.parquet")
        df = pd.DataFrame(papers)
        df.to_parquet(intermediate_file, index=False)
        logger.info(f"Saved intermediate results to {intermediate_file}")
    
    def save_to_parquet(self, papers: List[Dict], filename: str = None):
        """保存到parquet文件"""
        if not papers:
            logger.warning("No papers to save")
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cs_papers_6months_{timestamp}.parquet"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 创建DataFrame并保存
        df = pd.DataFrame(papers)
        
        # 数据清理和优化
        df = self.clean_dataframe(df)
        
        df.to_parquet(filepath, index=False, compression='snappy')
        
        # 输出统计信息
        self.print_statistics(df, filepath)
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理和优化DataFrame"""
        logger.info("Cleaning and optimizing data...")
        
        # 去重 - 基于arxiv_id
        initial_count = len(df)
        df = df.drop_duplicates(subset=['arxiv_id'], keep='last')
        logger.info(f"Removed {initial_count - len(df)} duplicates")
        
        # 转换日期类型
        df['date_submitted'] = pd.to_datetime(df['date_submitted'])
        df['last_updated'] = pd.to_datetime(df['last_updated'])
        df['fetch_time'] = pd.to_datetime(df['fetch_time'])
        
        # 清理文本字段
        text_columns = ['title', 'abstract', 'authors']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].str.strip()
                df[col] = df[col].replace('', None)  # 空字符串转为None
        
        # 优化内存使用
        df['arxiv_id'] = df['arxiv_id'].astype('category')
        
        # 按时间排序
        df = df.sort_values('date_submitted', ascending=False)
        
        return df
    
    def print_statistics(self, df: pd.DataFrame, filepath: str):
        """打印数据统计信息"""
        logger.info("="*50)
        logger.info("📊 Data Statistics")
        logger.info("="*50)
        logger.info(f"📁 File saved to: {filepath}")
        logger.info(f"📄 Total papers: {len(df):,}")
        logger.info(f"💾 File size: {os.path.getsize(filepath) / 1024 / 1024:.2f} MB")
        
        # 时间范围
        min_date = df['date_submitted'].min()
        max_date = df['date_submitted'].max()
        logger.info(f"📅 Date range: {min_date.date()} to {max_date.date()}")
        
        # 分类统计
        if 'cs_categories' in df.columns:
            # 展开分类统计
            all_categories = []
            for cats in df['cs_categories'].dropna():
                all_categories.extend(cats.split('; '))
            
            from collections import Counter
            cat_counts = Counter(all_categories)
            
            logger.info(f"🏷️  Top 10 CS categories:")
            for cat, count in cat_counts.most_common(10):
                logger.info(f"   {cat}: {count:,}")
        
        # 按月统计
        monthly_counts = df.groupby(df['date_submitted'].dt.to_period('M')).size()
        logger.info(f"📈 Papers by month:")
        for month, count in monthly_counts.items():
            logger.info(f"   {month}: {count:,}")
        
        logger.info("="*50)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量获取arXiv CS领域论文元数据")
    parser.add_argument("--output-dir", default="arxiv_data", 
                        help="输出目录 (默认: arxiv_data)")
    parser.add_argument("--months", type=int, default=6,
                        help="获取最近N个月的论文 (默认: 6)")
    parser.add_argument("--max-papers", type=int,
                        help="最大论文数量限制")
    parser.add_argument("--filename", 
                        help="输出文件名 (默认: 自动生成)")
    parser.add_argument("--verbose", action="store_true",
                        help="详细日志输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建获取器
    fetcher = ArxivBulkFetcher(args.output_dir, args.months)
    
    try:
        logger.info("🚀 Starting bulk CS papers metadata fetch...")
        logger.info(f"📁 Output directory: {args.output_dir}")
        logger.info(f"📅 Time range: last {args.months} months")
        if args.max_papers:
            logger.info(f"📊 Max papers: {args.max_papers:,}")
        
        # 获取论文元数据
        papers = fetcher.fetch_all_cs_papers(args.max_papers)
        
        if papers:
            # 保存到parquet
            fetcher.save_to_parquet(papers, args.filename)
            logger.info("✅ Bulk fetch completed successfully!")
        else:
            logger.warning("⚠️  No papers were fetched")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())