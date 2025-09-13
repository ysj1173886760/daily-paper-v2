#!/usr/bin/env python3
"""
从筛选结果中提取包含"graph"关键词的论文
输出格式：
## 论文标题
论文摘要内容
"""

import json
import argparse
import os
import re
import pandas as pd
from typing import List, Dict, Any


def extract_graph_papers(json_file: str, parquet_file: str = None, output_file: str = None):
    """
    从JSON文件中提取标题或摘要包含"graph"的论文
    
    Args:
        json_file: 筛选结果JSON文件路径
        parquet_file: 包含abstract的parquet文件路径
        output_file: 输出文件路径，如果为None则输出到控制台
    """
    print(f"📖 Loading filtered papers from: {json_file}")
    
    try:
        # 加载筛选结果
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查JSON结构
        if isinstance(data, dict) and "papers" in data:
            papers = data["papers"]
            print(f"📊 JSON contains metadata and {len(papers)} papers")
        elif isinstance(data, list):
            papers = data
            print(f"📊 Total papers loaded: {len(papers)}")
        else:
            print(f"❌ Unexpected JSON structure: {type(data)}")
            return []
        
        # 筛选相关论文（标记为目标论文的）
        relevant_papers = [p for p in papers if p.get("is_target_paper", False)]
        print(f"🎯 Relevant papers: {len(relevant_papers)}")
        
        # 加载parquet文件获取abstract
        if parquet_file:
            print(f"📖 Loading abstracts from: {parquet_file}")
            df = pd.read_parquet(parquet_file)
            print(f"📊 Parquet contains {len(df)} papers")
            
            # 创建arxiv_id到abstract的映射
            abstract_map = {}
            for _, row in df.iterrows():
                arxiv_id = row.get('arxiv_id', '')
                abstract = row.get('abstract', '')
                if arxiv_id and abstract:
                    abstract_map[arxiv_id] = abstract
            
            print(f"📝 Found abstracts for {len(abstract_map)} papers")
        else:
            abstract_map = {}
            print("⚠️  No parquet file provided, abstracts will be empty")
        
        # 查找包含"graph"的论文
        graph_papers = []
        graph_pattern = re.compile(r'graph', re.IGNORECASE)
        
        for paper in relevant_papers:
            title = paper.get('title', '')
            arxiv_id = paper.get('arxiv_id', '')
            abstract = abstract_map.get(arxiv_id, '')
            
            # 检查标题或摘要是否包含"graph"
            if graph_pattern.search(title) or graph_pattern.search(abstract):
                # 将abstract添加到paper中
                paper_with_abstract = paper.copy()
                paper_with_abstract['abstract'] = abstract
                graph_papers.append(paper_with_abstract)
        
        print(f"📈 Papers containing 'graph': {len(graph_papers)}")
        
        # 准备输出内容
        output_lines = []
        
        for i, paper in enumerate(graph_papers, 1):
            title = paper.get('title', 'Unknown Title').strip()
            abstract = paper.get('abstract', 'No abstract available').strip()
            arxiv_id = paper.get('arxiv_id', 'N/A')
            score = paper.get('overall_score', 0)
            
            # 格式化输出
            output_lines.append(f"## {title}")
            output_lines.append(f"{abstract}")
            output_lines.append(f"<!-- ArXiv ID: {arxiv_id}, Score: {score} -->")
            output_lines.append("")  # 空行分隔
            
            # 控制台显示进度
            if i <= 5:  # 只显示前5个
                print(f"\n{i}. {title[:100]}...")
        
        # 输出结果
        output_content = "\n".join(output_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"\n💾 Results saved to: {output_file}")
        else:
            print("\n" + "="*80)
            print("GRAPH PAPERS EXTRACTION RESULTS")
            print("="*80)
            print(output_content)
        
        return graph_papers
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return []
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return []


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="从筛选结果中提取包含'graph'关键词的论文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 从最新的筛选结果中提取（自动查找parquet文件）
  python scripts/extract_graph_papers.py
  
  # 指定JSON和parquet文件
  python scripts/extract_graph_papers.py --input arxiv_data/graph_ai_papers_20250813_144726.json --parquet arxiv_data/cs_papers_6months_20250812_002744.parquet
  
  # 保存到文件
  python scripts/extract_graph_papers.py --output graph_papers_extracted.md
  
  # 完整指定所有参数
  python scripts/extract_graph_papers.py --input arxiv_data/graph_ai_papers_20250813_144726.json --parquet arxiv_data/cs_papers_6months_20250812_002744.parquet --output results/graph_papers.md
        """
    )
    
    parser.add_argument("--input", "-i", 
                        help="输入的JSON文件路径（默认使用arxiv_data目录下最新的文件）")
    parser.add_argument("--parquet", "-p", 
                        help="包含abstract的parquet文件路径（默认使用arxiv_data目录下最新的文件）")
    parser.add_argument("--output", "-o", 
                        help="输出文件路径（默认输出到控制台）")
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.input:
        input_file = args.input
    else:
        # 查找arxiv_data目录下最新的graph_ai_papers文件
        arxiv_dir = "arxiv_data"
        if os.path.exists(arxiv_dir):
            json_files = [f for f in os.listdir(arxiv_dir) 
                         if f.startswith("graph_ai_papers_") and f.endswith(".json") 
                         and not f.endswith("_checkpoint.json")]
            
            if json_files:
                # 按文件名排序，取最新的
                latest_file = sorted(json_files)[-1]
                input_file = os.path.join(arxiv_dir, latest_file)
                print(f"🔍 Using latest file: {input_file}")
            else:
                print("❌ No graph_ai_papers JSON files found in arxiv_data directory")
                return
        else:
            print("❌ arxiv_data directory not found")
            return
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return
    
    # 确定parquet文件
    if args.parquet:
        parquet_file = args.parquet
    else:
        # 查找arxiv_data目录下最新的cs_papers parquet文件
        arxiv_dir = "arxiv_data"
        if os.path.exists(arxiv_dir):
            parquet_files = [f for f in os.listdir(arxiv_dir) 
                           if f.startswith("cs_papers_") and f.endswith(".parquet")]
            
            if parquet_files:
                # 按文件名排序，取最新的
                latest_parquet = sorted(parquet_files)[-1]
                parquet_file = os.path.join(arxiv_dir, latest_parquet)
                print(f"🔍 Using latest parquet file: {parquet_file}")
            else:
                print("⚠️  No cs_papers parquet files found in arxiv_data directory")
                parquet_file = None
        else:
            parquet_file = None
    
    # 检查parquet文件是否存在
    if parquet_file and not os.path.exists(parquet_file):
        print(f"❌ Parquet file not found: {parquet_file}")
        parquet_file = None
    
    # 确定输出文件
    output_file = args.output
    if output_file:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 Created output directory: {output_dir}")
    
    # 执行提取
    graph_papers = extract_graph_papers(input_file, parquet_file, output_file)
    
    if graph_papers:
        print(f"\n✅ Successfully extracted {len(graph_papers)} papers containing 'graph'")
        if not output_file:
            print("\n💡 Use --output to save results to a file")
    else:
        print("\n❌ No papers found or extraction failed")


if __name__ == "__main__":
    main()