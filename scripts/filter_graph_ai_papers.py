#!/usr/bin/env python3
"""
使用LLM筛选Graph + AI相关论文
专注于识别图神经网络、知识图谱、GraphRAG等领域的综述论文和重要研究
"""

import pandas as pd
import os
import sys
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from json_repair import repair_json
from tqdm.asyncio import tqdm

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daily_paper.utils.call_llm import LLM, AsyncLLM


class GraphAIPaperFilter:
    def __init__(self, 
                 llm_base_url: Optional[str] = None,
                 llm_api_key: Optional[str] = None,
                 llm_model: str = "gpt-4",
                 temperature: float = 0.1,
                 batch_size: int = 10,
                 max_concurrent: int = 32,
                 rate_limit_delay: float = 0.1,
                 enable_concurrent: bool = True,
                 save_all_evaluations: bool = False,
                 save_token_stats: bool = False,
                 save_progress: bool = False,
                 save_report: bool = False,
                 resume_from_checkpoint: bool = False):
        """
        初始化Graph + AI论文筛选器
        
        Args:
            llm_base_url: LLM API基础URL
            llm_api_key: LLM API密钥
            llm_model: 使用的模型名称
            temperature: 模型温度参数
            batch_size: 批处理大小
            max_concurrent: 最大并发数
            rate_limit_delay: 速率限制延迟
            enable_concurrent: 是否启用并发
            save_all_evaluations: 是否保存所有评估结果
            save_token_stats: 是否保存token统计文件
            save_progress: 是否保存进度文件
            save_report: 是否生成文本报告
        """
        self.config = {
            "llm_base_url": llm_base_url or os.getenv("LLM_BASE_URL"),
            "llm_api_key": llm_api_key or os.getenv("LLM_API_KEY"),
            "llm_model": llm_model,
            "temperature": temperature,
            "batch_size": batch_size,
            "max_concurrent": max_concurrent,
            "rate_limit_delay": rate_limit_delay,
            "enable_concurrent": enable_concurrent,
            "save_all_evaluations": save_all_evaluations,
            "save_token_stats": save_token_stats,
            "save_progress": save_progress,
            "save_report": save_report,
            "resume_from_checkpoint": resume_from_checkpoint
        }
        
        self._init_llm()
        self.criteria = self._define_filtering_criteria()
        
        # Token使用统计
        self.token_stats = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
            "model": self.config["llm_model"],
            "per_call_stats": []
        }
    
    def _filter_by_time(self, df: pd.DataFrame, months: Optional[int] = None) -> pd.DataFrame:
        """
        根据时间过滤论文
        
        Args:
            df: 论文数据DataFrame
            months: 过滤多少个月内的论文，None表示不过滤
            
        Returns:
            过滤后的DataFrame
        """
        if months is None:
            return df
        
        # 计算时间阈值
        cutoff_date = datetime.now() - timedelta(days=months * 30)  # 近似按30天/月计算
        
        # 确保date_submitted列是datetime类型
        if 'date_submitted' in df.columns:
            df = df.copy()
            df['date_submitted'] = pd.to_datetime(df['date_submitted'])
            
            # 过滤时间
            filtered_df = df[df['date_submitted'] >= cutoff_date]
            
            print(f"⏰ Time filtering: {months} months")
            print(f"   Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
            print(f"   Before filtering: {len(df):,} papers")
            print(f"   After filtering: {len(filtered_df):,} papers")
            print(f"   Filtered out: {len(df) - len(filtered_df):,} papers")
            
            return filtered_df
        else:
            print("⚠️  Warning: 'date_submitted' column not found, skipping time filtering")
            return df
    
    def _init_llm(self):
        """初始化LLM实例"""
        self.llm = LLM(
            llm_base_url=self.config["llm_base_url"],
            llm_api_key=self.config["llm_api_key"],
            llm_model=self.config["llm_model"],
        )
        self.async_llm = AsyncLLM(
            llm_base_url=self.config["llm_base_url"],
            llm_api_key=self.config["llm_api_key"],
            llm_model=self.config["llm_model"],
        )
    
    def _define_filtering_criteria(self) -> Dict[str, Any]:
        """定义筛选标准"""
        return {
            "target_domains": [
                "Graph Neural Networks (GNNs)",
                "Knowledge Graphs and AI",
                "Graph Foundation Models",
                "GraphRAG (Retrieval-Augmented Generation with Graphs)",
                "Graph Machine Learning",
                "AI applications on graph structures",
                "Graph-based reasoning and inference",
                "Multi-modal graph learning",
                "Graph transformers and attention mechanisms",
                "Large Language Models on graphs"
            ],
            "survey_types": [
                "Survey papers (系统性综述)",
                "Review papers (回顾性综述)", 
                "Comprehensive studies (全面性研究)",
                "Tutorial papers (教程性论文)",
                "Overview papers (概述性论文)",
                "Progress reports (进展报告)",
                "State-of-the-art reviews (最新技术综述)"
            ],
            "survey_keywords": [
                # 综述类型关键词（标题中的强指示词）
                "survey", "review", "comprehensive study", "systematic review",
                "tutorial", "overview", "progress", "advances", "recent advances",
                "state-of-the-art", "comparison", "comparative study",
                
                # 综述描述词（摘要中的指示词）
                "systematic review", "comprehensive overview", "recent developments",
                "comparative analysis", "literature review", "field overview",
                "taxonomy", "classification", "categorization",
                
                # Graph + AI 领域关键词
                "graph neural network", "GNN", "graph transformer", 
                "knowledge graph", "KG", "graph foundation model",
                "graphrag", "graph-rag", "graph machine learning",
                "graph AI", "graph reasoning", "graph representation",
                "message passing", "graph attention", "graph convolution",
                "multi-modal graph", "heterogeneous graph", "temporal graph"
            ]
        }
    
    def _create_evaluation_prompt(self, paper: Dict[str, Any]) -> str:
        """创建LLM评估提示"""
        
        domains_str = "\n".join(f"- {domain}" for domain in self.criteria["target_domains"])
        
        prompt = f"""你是一个专业的学术论文筛选专家，专注于识别Graph + AI领域的综述论文。

**重要提醒：我只对综述/调研类论文感兴趣，请严格筛选！**

我关注的领域：
{domains_str}

**综述论文识别标准：**
- 标题包含：Survey, Review, Comprehensive Study, Tutorial, Overview, Progress, Advances等
- 摘要描述：系统性回顾、全面综述、最新进展、比较分析、领域概览等
- 内容特征：涵盖多个方法、比较不同技术、总结领域发展、提供分类框架等

论文信息：
标题：{paper.get('title', 'N/A')}
摘要：{paper.get('abstract', 'N/A')}
分类：{paper.get('cs_categories', 'N/A')}

请严格按照以下标准评估（只有综述论文才应该得到高分）：

1. **领域相关性** (1-10分)：
   - 9-10分：Graph + AI核心领域的综述
   - 7-8分：相关领域的综述（如机器学习、深度学习综述涉及图方法）
   - 5-6分：边缘相关的综述
   - 1-4分：不相关或非综述论文

2. **综述特征** (1-10分)：
   - 9-10分：明显的综述论文，标题含Survey/Review等，摘要描述系统性回顾
   - 7-8分：综述性质明显，但可能不是传统综述格式
   - 5-6分：有一定综述性质，但主要是原创研究
   - 3-4分：轻微综述内容，主要是方法论文
   - 1-2分：完全不是综述，纯粹的原创研究或应用论文

3. **综述质量** (1-10分)：
   - 9-10分：全面深入的领域综述，具有重要参考价值
   - 7-8分：质量较高的综述，覆盖面广
   - 5-6分：一般性综述
   - 3-4分：综述质量有限
   - 1-2分：非综述或质量很低

**评判规则：**
- 只有同时满足"领域相关"和"确实是综述"的论文才能被标记为目标论文
- 纯粹的方法论文、应用论文、实验论文等一律排除
- 宁可漏掉也不要误判非综述论文

请以以下JSON格式返回评估结果：
{{
    "relevance_score": <1-10的数字>,
    "survey_score": <1-10的数字>,
    "quality_score": <1-10的数字>,
    "overall_score": <平均分>,
    "is_target_paper": <true/false，必须是综述且overall_score >= 7.0>,
    "is_survey": <true/false，判断是否为综述论文>,
    "reasoning": "<简要说明评判理由，重点说明是否为综述>",
    "survey_indicators": ["<综述特征1>", "<综述特征2>", "..."],
    "key_topics": ["<主要主题1>", "<主题2>", "..."]
}}

只返回JSON，不要其他文字。"""
        
        return prompt
    
    async def _evaluate_paper_async(self, paper: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        """异步评估单篇论文"""
        async with semaphore:  # 限制并发数
            try:
                # 添加速率限制延迟
                if self.config["rate_limit_delay"] > 0:
                    await asyncio.sleep(self.config["rate_limit_delay"])
                
                prompt = self._create_evaluation_prompt(paper)
                
                # 异步调用LLM并收集token使用信息
                response, usage_info = await self.async_llm.achat(
                    prompt,
                    temperature=self.config["temperature"],
                    return_usage=True,
                )
                
                # 更新token统计（需要同步）
                self._update_token_stats(usage_info, paper.get("arxiv_id", "unknown"))
                
                # 解析LLM响应
                response = response.strip()
                
                # 尝试清理markdown格式
                if response.startswith("```json"):
                    response = response[7:]
                elif response.startswith("```"):
                    response = response[3:]
                    
                if response.endswith("```"):
                    response = response[:-3]
                
                response = response.strip()
                
                # 尝试解析JSON，如果失败则记录详细信息
                try:
                    result = json.loads(response)
                except json.JSONDecodeError as json_error:
                    # 记录解析失败的详细信息
                    # print(f"🚫 JSON parsing failed for paper {paper.get('arxiv_id', 'unknown')}:")
                    # print(f"   Error: {str(json_error)}")
                    # print(f"   Response length: {len(response)}")
                    # print(f"   First 200 chars: {response[:200]!r}")
                    # if len(response) > 200:
                    #     print(f"   Last 100 chars: {response[-100:]!r}")
                    
                    # 使用json_repair尝试修复JSON
                    try:
                        fixed_response = repair_json(response)
                        result = json.loads(fixed_response)
                        # print(f"✅ JSON parsing succeeded after repair_json fix")
                    except Exception as repair_error:
                        print(f"❌ json_repair also failed: {str(repair_error)}")
                        raise json_error  # 如果修复后还是失败，抛出原始错误
                
                # 添加论文基本信息和token使用信息
                result.update({
                    "arxiv_id": paper.get("arxiv_id"),
                    "title": paper.get("title"),
                    "authors": paper.get("authors"),
                    "cs_categories": paper.get("cs_categories"),
                    "date_submitted": str(paper.get("date_submitted", "")),
                    "evaluation_time": datetime.now().isoformat(),
                    "token_usage": usage_info
                })
                
                return result
                
            except Exception as e:
                print(f"⚠️  Error evaluating paper {paper.get('arxiv_id', 'unknown')}: {str(e)}")
                return {
                    "arxiv_id": paper.get("arxiv_id"),
                    "title": paper.get("title"),
                    "error": str(e),
                    "is_target_paper": False,
                    "overall_score": 0,
                    "evaluation_time": datetime.now().isoformat(),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": self.config["llm_model"]}
                }
    
    def _update_token_stats(self, usage_info: Dict[str, Any], arxiv_id: str):
        """更新token使用统计"""
        self.token_stats["total_prompt_tokens"] += usage_info.get("prompt_tokens", 0)
        self.token_stats["total_completion_tokens"] += usage_info.get("completion_tokens", 0) 
        self.token_stats["total_tokens"] += usage_info.get("total_tokens", 0)
        self.token_stats["api_calls"] += 1
        
        # 记录单次调用的详细信息
        call_stat = {
            "arxiv_id": arxiv_id,
            "timestamp": datetime.now().isoformat(),
            **usage_info
        }
        self.token_stats["per_call_stats"].append(call_stat)
    
    def _estimate_cost(self) -> Dict[str, float]:
        """估算API调用费用（基于OpenAI GPT-4定价）"""
        # GPT-4 定价（可能需要根据实际模型调整）
        pricing = {
            "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},  # 每1k token的价格
            "gpt-4-turbo": {"input": 0.01 / 1000, "output": 0.03 / 1000},
            "gpt-3.5-turbo": {"input": 0.0015 / 1000, "output": 0.002 / 1000},
        }
        
        model = self.token_stats["model"].lower()
        # 尝试匹配模型定价
        model_pricing = None
        for model_key, price in pricing.items():
            if model_key in model:
                model_pricing = price
                break
        
        if not model_pricing:
            model_pricing = pricing["gpt-4"]  # 默认使用GPT-4定价
        
        input_cost = self.token_stats["total_prompt_tokens"] * model_pricing["input"]
        output_cost = self.token_stats["total_completion_tokens"] * model_pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input_cost_usd": round(input_cost, 4),
            "output_cost_usd": round(output_cost, 4),
            "total_cost_usd": round(total_cost, 4),
            "pricing_model": model_pricing,
            "cost_per_paper": round(total_cost / max(self.token_stats["api_calls"], 1), 4)
        }
    
    def get_token_summary(self) -> Dict[str, Any]:
        """获取token使用总结"""
        cost_estimate = self._estimate_cost()
        
        return {
            "token_statistics": self.token_stats.copy(),
            "cost_estimate": cost_estimate,
            "efficiency_metrics": {
                "avg_prompt_tokens": round(self.token_stats["total_prompt_tokens"] / max(self.token_stats["api_calls"], 1), 1),
                "avg_completion_tokens": round(self.token_stats["total_completion_tokens"] / max(self.token_stats["api_calls"], 1), 1),
                "avg_total_tokens": round(self.token_stats["total_tokens"] / max(self.token_stats["api_calls"], 1), 1),
                "total_api_calls": self.token_stats["api_calls"]
            }
        }
    
    def _get_checkpoint_file_path(self, output_file: str) -> str:
        """生成checkpoint文件路径"""
        base_name = os.path.splitext(output_file)[0]
        return f"{base_name}_checkpoint.json"
    
    
    def _save_checkpoint(self, processed_papers: List[Dict[str, Any]], 
                        current_batch: int, total_batches: int,
                        output_file: str):
        """保存checkpoint到JSON文件"""
        if not processed_papers:
            return
            
        checkpoint_file = self._get_checkpoint_file_path(output_file)
        
        # 创建checkpoint数据
        checkpoint_data = {
            "metadata": {
                "current_batch": current_batch,
                "total_batches": total_batches,
                "total_processed": len(processed_papers),
                "timestamp": datetime.now().isoformat(),
                "token_stats": self.token_stats.copy()
            },
            "processed_papers": processed_papers
        }
        
        # 保存为JSON文件
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"📋 Checkpoint saved: {checkpoint_file} ({len(processed_papers)} papers)")
        except Exception as e:
            print(f"❌ Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self, output_file: str) -> Optional[Dict[str, Any]]:
        """从checkpoint文件加载进度"""
        checkpoint_file = self._get_checkpoint_file_path(output_file)
        
        if not os.path.exists(checkpoint_file):
            print("📋 No checkpoint found, starting fresh")
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            metadata = checkpoint_data["metadata"]
            processed_papers = checkpoint_data["processed_papers"]
            
            print(f"📋 Checkpoint loaded: {len(processed_papers)} papers processed, "
                  f"batch {metadata['current_batch']}/{metadata['total_batches']}")
            
            return checkpoint_data
        
        except Exception as e:
            print(f"⚠️  Failed to load checkpoint: {str(e)}")
            return None
    
    def _cleanup_checkpoint(self, output_file: str):
        """清理checkpoint文件"""
        checkpoint_file = self._get_checkpoint_file_path(output_file)
        if os.path.exists(checkpoint_file):
            try:
                os.remove(checkpoint_file)
                print(f"🗑️  Checkpoint file cleaned up: {checkpoint_file}")
            except Exception as e:
                print(f"⚠️  Failed to cleanup checkpoint: {str(e)}")
    
    def evaluate_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """评估单篇论文"""
        try:
            prompt = self._create_evaluation_prompt(paper)
            
            # 调用LLM并收集token使用信息
            response, usage_info = self.llm.chat(
                prompt,
                temperature=self.config["temperature"],
                return_usage=True,
            )
            
            # 更新token统计
            self._update_token_stats(usage_info, paper.get("arxiv_id", "unknown"))
            
            # 解析LLM响应
            # 尝试提取JSON内容
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            if response.startswith("```"):
                response = response[3:]
                
            result = json.loads(response.strip())
            
            # 添加论文基本信息和token使用信息
            result.update({
                "arxiv_id": paper.get("arxiv_id"),
                "title": paper.get("title"),
                "authors": paper.get("authors"),
                "cs_categories": paper.get("cs_categories"),
                "date_submitted": str(paper.get("date_submitted", "")),
                "evaluation_time": datetime.now().isoformat(),
                "token_usage": usage_info
            })
            
            return result
            
        except Exception as e:
            print(f"⚠️  Error evaluating paper {paper.get('arxiv_id', 'unknown')}: {str(e)}")
            return {
                "arxiv_id": paper.get("arxiv_id"),
                "title": paper.get("title"),
                "error": str(e),
                "is_target_paper": False,
                "overall_score": 0,
                "evaluation_time": datetime.now().isoformat(),
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": self.config["llm_model"]}
            }
    
    async def _evaluate_papers_concurrent(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并发评估多篇论文 - 带进度条显示"""
        max_concurrent = self.config["max_concurrent"]
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 创建异步任务
        tasks = [
            self._evaluate_paper_async(paper, semaphore) 
            for paper in papers
        ]
        
        # 使用tqdm显示批次内进度，并发执行所有任务
        # 创建进度条
        progress_bar = tqdm(
            total=len(papers), 
            desc=f"📝 Processing", 
            unit="paper", 
            leave=False,
            ncols=80,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        # 包装任务以更新进度条
        async def track_progress(task):
            result = await task
            progress_bar.update(1)
            return result
        
        # 执行带进度跟踪的任务
        tracked_tasks = [track_progress(task) for task in tasks]
        results = await asyncio.gather(*tracked_tasks, return_exceptions=True)
        progress_bar.close()
        
        # 统计结果
        successful_count = sum(1 for r in results if not isinstance(r, Exception) and not r.get("error"))
        error_count = len(results) - successful_count
        if error_count > 0:
            print(f"   ⚠️  {error_count} errors occurred during processing")
        
        # 处理异常情况
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"⚠️  Exception in paper {papers[i].get('arxiv_id', 'unknown')}: {str(result)}")
                processed_results.append({
                    "arxiv_id": papers[i].get("arxiv_id"),
                    "title": papers[i].get("title"),
                    "error": str(result),
                    "is_target_paper": False,
                    "overall_score": 0,
                    "evaluation_time": datetime.now().isoformat(),
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": self.config["llm_model"]}
                })
            else:
                processed_results.append(result)
                
        return processed_results

    async def _evaluate_papers_concurrent_with_cleanup(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """带清理功能的并发评估论文"""
        try:
            results = await self._evaluate_papers_concurrent(papers)
            return results
        finally:
            # 确保AsyncClient正确关闭，防止event loop错误
            try:
                await self.async_llm.aclose()
            except Exception:
                pass  # 忽略清理时的异常

    def filter_papers(self, data_file: str, output_file: Optional[str] = None, 
                     max_papers: Optional[int] = None, start_index: int = 0,
                     months_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        筛选论文
        
        Args:
            data_file: 输入的parquet文件路径
            output_file: 输出文件路径
            max_papers: 最大处理论文数量
            start_index: 开始处理的索引
            months_filter: 过滤最近N个月的论文
        """
        print(f"📖 Loading papers from: {data_file}")
        df = pd.read_parquet(data_file)
        print(f"📊 Total papers in file: {len(df):,}")
        
        # 应用时间过滤
        df = self._filter_by_time(df, months_filter)
        
        # 应用索引和数量限制
        if max_papers:
            end_index = min(start_index + max_papers, len(df))
            df = df.iloc[start_index:end_index]
            print(f"🔢 Limited to {max_papers} papers starting from index {start_index}")
        else:
            df = df.iloc[start_index:]
            if start_index > 0:
                print(f"🔢 Starting from index {start_index}")
        
        print(f"📋 Final paper count to analyze: {len(df):,}")
        if len(df) == 0:
            print("❌ No papers to analyze after filtering. Exiting.")
            return []
        
        # 显示处理模式和checkpoint状态
        if self.config["enable_concurrent"]:
            print(f"🚀 Using concurrent processing with max {self.config['max_concurrent']} concurrent requests")
            if self.config["save_progress"]:
                print("📋 Checkpoint enabled: progress will be saved after each batch")
                if self.config["resume_from_checkpoint"]:
                    print("🔄 Resume mode: will attempt to load from checkpoint if exists")
            else:
                print("📋 Checkpoint disabled: no progress saving")
            return self._filter_papers_concurrent(df, output_file, start_index)
        else:
            print("🔄 Using sequential processing")
            return self._filter_papers_sequential(df, output_file, start_index)
    
    def _filter_papers_concurrent(self, df: pd.DataFrame, output_file: Optional[str], start_index: int = 0) -> List[Dict[str, Any]]:
        """
        并发模式筛选论文 - 基于batch的处理和checkpoint机制
        
        特性:
        - Batch内并发处理，batch间顺序执行
        - 每个batch完成后保存checkpoint
        - 支持断点续传
        - 实时显示batch内处理进度条
        """
        # 确定实际的输出文件路径（用于checkpoint）
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            actual_output_file = f"arxiv_data/graph_ai_papers_{timestamp}.json"
        else:
            actual_output_file = output_file
            
        # 显示checkpoint信息
        if self.config["save_progress"]:
            checkpoint_file = self._get_checkpoint_file_path(actual_output_file)
            print(f"   Checkpoint location: {checkpoint_file}")
        
        results = []
        relevant_papers = []
        batch_size = self.config["batch_size"]
        
        # 计算批次信息
        total_batches = (len(df) + batch_size - 1) // batch_size
        current_batch_start = 0
        
        # 尝试从checkpoint恢复 (只有当save_progress启用时)
        if self.config["resume_from_checkpoint"] and self.config["save_progress"]:
            checkpoint = self._load_checkpoint(actual_output_file)
            if checkpoint:
                results = checkpoint["processed_papers"]
                relevant_papers = [p for p in results if p.get("is_target_paper", False)]
                current_batch_start = checkpoint["metadata"]["current_batch"] * batch_size
                
                # 恢复token统计
                if "token_stats" in checkpoint["metadata"]:
                    saved_stats = checkpoint["metadata"]["token_stats"]
                    self.token_stats.update(saved_stats)
                
                print(f"🔄 Resuming from batch {checkpoint['metadata']['current_batch'] + 1}/{total_batches}")
                print(f"📊 Already processed {len(results)} papers, {len(relevant_papers)} relevant")
        
        # 按批处理 - batch内并发，batch间顺序执行
        for batch_idx in range(current_batch_start // batch_size, total_batches):
            try:
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, len(df))
                batch_df = df.iloc[batch_start:batch_end]
                
                print(f"🔄 Processing batch {batch_idx + 1}/{total_batches}: papers {batch_start + 1}-{batch_end}")
                
                # 转换为字典列表
                batch_papers = [row.to_dict() for _, row in batch_df.iterrows()]
                
                # 异步评估这一批论文 (batch内并发，带进度条)
                batch_results = asyncio.run(self._evaluate_papers_concurrent_with_cleanup(batch_papers))
                
            except Exception as batch_error:
                print(f"❌ Critical error in batch {batch_idx + 1}: {str(batch_error)}")
                print(f"⚠️  Skipping this batch and continuing with next batch...")
                
                # 创建空的batch结果来保持一致性
                batch_results = []
                for paper in batch_papers if 'batch_papers' in locals() else []:
                    batch_results.append({
                        "arxiv_id": paper.get("arxiv_id", "unknown"),
                        "title": paper.get("title", "Unknown"),
                        "error": f"Batch processing error: {str(batch_error)}",
                        "is_target_paper": False,
                        "overall_score": 0,
                        "evaluation_time": datetime.now().isoformat(),
                        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": self.config["llm_model"]}
                    })
                
                # 继续到下一个batch
                continue
            
            # 处理批次结果
            batch_relevant_count = 0
            for result in batch_results:
                try:
                    results.append(result)
                    
                    if result.get("is_target_paper", False):
                        relevant_papers.append(result)
                        batch_relevant_count += 1
                        
                        # 安全的字符串格式化
                        title = result.get('title', 'Unknown')
                        if isinstance(title, str):
                            title_display = title[:80] + "..." if len(title) > 80 else title
                        else:
                            title_display = str(title)[:80] + "..."
                        
                        # 安全的分数格式化
                        try:
                            score = float(result.get('overall_score', 0))
                            score_display = f"{score:.1f}"
                        except (ValueError, TypeError):
                            score_display = str(result.get('overall_score', 'N/A'))
                        
                        # 安全的主题列表格式化
                        topics = result.get('key_topics', [])
                        if isinstance(topics, list):
                            topics_display = topics
                        else:
                            topics_display = [str(topics)]
                        
                        print(f"✅ Found relevant paper: {title_display}")
                        print(f"   Score: {score_display}, Topics: {topics_display}")
                        
                except Exception as format_error:
                    print(f"⚠️  Error formatting result display for paper {result.get('arxiv_id', 'unknown')}: {str(format_error)}")
                    # 仍然添加到结果中，但使用简化显示
                    results.append(result)
                    if result.get("is_target_paper", False):
                        relevant_papers.append(result)
                        batch_relevant_count += 1
                        print(f"✅ Found relevant paper (display error): {result.get('arxiv_id', 'unknown')}")
            
            # 批次完成后立即保存checkpoint (如果启用了save_progress)
            if self.config["save_progress"]:
                self._save_checkpoint(results, batch_idx, total_batches, actual_output_file)
            
            # 显示批次统计
            print(f"📊 Batch {batch_idx + 1}/{total_batches} completed. Found {batch_relevant_count} relevant in this batch.")
            
            # 安全的百分比计算
            try:
                if len(results) > 0:
                    percentage = len(relevant_papers) / len(results) * 100
                    print(f"📈 Total: {len(relevant_papers)}/{len(results)} relevant ({percentage:.1f}%)")
                else:
                    print(f"📈 Total: {len(relevant_papers)}/0 relevant (N/A%)")
            except Exception as calc_error:
                print(f"📈 Total: {len(relevant_papers)}/{len(results)} relevant (calc error: {str(calc_error)})")
            
            if self.token_stats["api_calls"] > 0:
                avg_tokens = self.token_stats["total_tokens"] / self.token_stats["api_calls"]
                estimated_cost = self._estimate_cost()["total_cost_usd"]
                print(f"💰 Token usage: {self.token_stats['total_tokens']:,} total, {avg_tokens:.1f} avg, ${estimated_cost:.4f} cost")
                
            print("-" * 50)
        
        # 最终保存并清理checkpoint
        self._save_final_results(results, relevant_papers, actual_output_file)
        # 只有启用了save_progress时才清理checkpoint
        if self.config["save_progress"]:
            self._cleanup_checkpoint(actual_output_file)
        
        return relevant_papers
    
    def _filter_papers_sequential(self, df: pd.DataFrame, output_file: Optional[str], start_index: int) -> List[Dict[str, Any]]:
        """顺序模式筛选论文（原有逻辑）"""
        results = []
        relevant_papers = []
        
        for idx, (_, paper) in enumerate(df.iterrows()):
            print(f"🔍 Evaluating paper {idx + 1}/{len(df)}: {paper['arxiv_id']}")
            
            result = self.evaluate_paper(paper.to_dict())
            results.append(result)
            
            if result.get("is_target_paper", False):
                relevant_papers.append(result)
                print(f"✅ Found relevant paper: {result.get('title', 'Unknown')[:80]}...")
                print(f"   Score: {result.get('overall_score', 0):.1f}, Topics: {result.get('key_topics', [])}")
            
            # 批量保存进度
            if (idx + 1) % self.config["batch_size"] == 0:
                self._save_progress(results, relevant_papers, output_file, start_index + idx + 1)
                
            # 避免API调用过快
            time.sleep(0.5)
        
        # 保存最终结果
        self._save_final_results(results, relevant_papers, output_file)
        
        return relevant_papers
    
    def _save_progress(self, all_results: List[Dict[str, Any]], 
                      relevant_papers: List[Dict[str, Any]], 
                      output_file: Optional[str], current_idx: int):
        """保存中间进度"""
        if not output_file or not self.config["save_progress"]:
            return
            
        base_name = os.path.splitext(output_file)[0]
        
        # 保存进度文件
        progress_file = f"{base_name}_progress_{current_idx}.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                "processed_count": len(all_results),
                "relevant_count": len(relevant_papers),
                "last_index": current_idx,
                "timestamp": datetime.now().isoformat(),
                "all_results": all_results,
                "relevant_papers": relevant_papers
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Progress saved: {progress_file} (Found {len(relevant_papers)} relevant papers)")
    
    def _save_final_results(self, all_results: List[Dict[str, Any]], 
                           relevant_papers: List[Dict[str, Any]], 
                           output_file: Optional[str]):
        """保存最终结果"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"arxiv_data/graph_ai_papers_{timestamp}.json"
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 获取token使用总结
        token_summary = self.get_token_summary()
        
        # 保存筛选出的相关论文（主要输出文件，始终保存）
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "total_evaluated": len(all_results),
                    "relevant_found": len(relevant_papers),
                    "success_rate": len(relevant_papers) / len(all_results) if all_results else 0,
                    "evaluation_time": datetime.now().isoformat(),
                    "criteria": self.criteria,
                    "token_usage": token_summary if self.config["save_token_stats"] else {
                        "total_api_calls": self.token_stats["api_calls"],
                        "total_tokens": self.token_stats["total_tokens"],
                        "estimated_cost_usd": self._estimate_cost()["total_cost_usd"]
                    }
                },
                "papers": relevant_papers
            }, f, ensure_ascii=False, indent=2)
        
        # 可选：保存所有评估结果
        all_results_file = None
        if self.config["save_all_evaluations"]:
            all_results_file = output_file.replace('.json', '_all_evaluations.json')
            with open(all_results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        # 可选：保存详细的token统计
        token_stats_file = None
        if self.config["save_token_stats"]:
            token_stats_file = output_file.replace('.json', '_token_stats.json')
            with open(token_stats_file, 'w', encoding='utf-8') as f:
                json.dump(token_summary, f, ensure_ascii=False, indent=2)
        
        # 可选：生成统计报告
        report_file = None
        if self.config["save_report"]:
            report_file = output_file.replace('.json', '_report.txt')
            self._generate_report(all_results, relevant_papers, report_file)
        
        print(f"✅ Results saved:")
        print(f"   🎯 Relevant papers: {output_file}")
        if all_results_file:
            print(f"   📄 All evaluations: {all_results_file}")
        if token_stats_file:
            print(f"   📊 Token statistics: {token_stats_file}")
        if report_file:
            print(f"   📋 Text report: {report_file}")
        # 安全的百分比计算
        try:
            if len(all_results) > 0:
                success_rate = len(relevant_papers) / len(all_results) * 100
                print(f"   📈 Found {len(relevant_papers)}/{len(all_results)} relevant survey papers ({success_rate:.1f}%)")
            else:
                print(f"   📈 Found {len(relevant_papers)}/0 relevant survey papers (N/A%)")
        except Exception as calc_error:
            print(f"   📈 Found {len(relevant_papers)}/{len(all_results)} relevant survey papers (calc error)")
        
        # 显示token使用统计
        cost_info = token_summary["cost_estimate"]
        efficiency = token_summary["efficiency_metrics"]
        print(f"\n💰 Token Usage Summary:")
        print(f"   Total API calls: {efficiency['total_api_calls']}")
        print(f"   Total tokens used: {self.token_stats['total_tokens']:,}")
        print(f"   Average tokens per call: {efficiency['avg_total_tokens']}")
        print(f"   Estimated cost: ${cost_info['total_cost_usd']:.4f} USD")
        print(f"   Cost per paper: ${cost_info['cost_per_paper']:.4f} USD")
    
    def _generate_report(self, all_results: List[Dict[str, Any]], 
                        relevant_papers: List[Dict[str, Any]], 
                        report_file: str):
        """生成统计报告"""
        token_summary = self.get_token_summary()
        cost_info = token_summary["cost_estimate"]
        efficiency = token_summary["efficiency_metrics"]
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("Graph + AI Paper Filtering Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"📊 Summary Statistics:\n")
            f.write(f"   Total papers evaluated: {len(all_results)}\n")
            f.write(f"   Relevant papers found: {len(relevant_papers)}\n")
            # 安全的成功率计算
            try:
                if len(all_results) > 0:
                    success_rate = len(relevant_papers) / len(all_results) * 100
                    f.write(f"   Success rate: {success_rate:.1f}%\n\n")
                else:
                    f.write(f"   Success rate: N/A%\n\n")
            except Exception:
                f.write(f"   Success rate: calculation error\n\n")
            
            # 添加token使用统计
            f.write(f"💰 Token Usage & Cost Analysis:\n")
            f.write(f"   Total API calls: {efficiency['total_api_calls']}\n")
            f.write(f"   Total tokens: {self.token_stats['total_tokens']:,}\n")
            f.write(f"     - Prompt tokens: {self.token_stats['total_prompt_tokens']:,}\n")
            f.write(f"     - Completion tokens: {self.token_stats['total_completion_tokens']:,}\n")
            f.write(f"   Average tokens per call: {efficiency['avg_total_tokens']:.1f}\n")
            f.write(f"   Estimated cost: ${cost_info['total_cost_usd']:.4f} USD\n")
            f.write(f"   Cost per paper: ${cost_info['cost_per_paper']:.4f} USD\n")
            f.write(f"   Model used: {self.token_stats['model']}\n\n")
            
            if relevant_papers:
                # 确保scores都是数字类型，避免dtype兼容性问题
                scores = []
                for p in relevant_papers:
                    score = p.get('overall_score', 0)
                    try:
                        # 强制转换为float
                        if isinstance(score, str):
                            # 如果是字符串，尝试提取数字
                            import re
                            numbers = re.findall(r'\d+\.?\d*', str(score))
                            score = float(numbers[0]) if numbers else 0.0
                        else:
                            score = float(score)
                    except (ValueError, TypeError):
                        score = 0.0
                    scores.append(score)
                
                f.write(f"🎯 Relevant Papers Analysis:\n")
                if scores:
                    # 使用Python内置函数计算，避免numpy的dtype问题
                    avg_score = sum(scores) / len(scores)
                    f.write(f"   Average score: {avg_score:.2f}\n")
                    f.write(f"   Score range: {min(scores):.1f} - {max(scores):.1f}\n\n")
                else:
                    f.write(f"   No valid scores available\n\n")
                
                f.write(f"📝 Top Papers (by score):\n")
                
                # 安全的排序，处理可能的数据类型问题
                def safe_score_key(paper):
                    score = paper.get('overall_score', 0)
                    try:
                        if isinstance(score, str):
                            import re
                            numbers = re.findall(r'\d+\.?\d*', str(score))
                            return float(numbers[0]) if numbers else 0.0
                        else:
                            return float(score)
                    except (ValueError, TypeError):
                        return 0.0
                
                sorted_papers = sorted(relevant_papers, key=safe_score_key, reverse=True)
                
                for i, paper in enumerate(sorted_papers[:10], 1):
                    f.write(f"\n{i}. {paper.get('title', 'Unknown')}\n")
                    f.write(f"   ArXiv ID: {paper.get('arxiv_id', 'N/A')}\n")
                    # 安全地显示分数
                    score = safe_score_key(paper)
                    f.write(f"   Score: {score:.1f}\n")
                    # 安全地处理列表字段
                    topics = paper.get('key_topics', [])
                    if isinstance(topics, list):
                        topics_str = ', '.join(topics)
                    else:
                        topics_str = str(topics) if topics else 'N/A'
                    f.write(f"   Topics: {topics_str}\n")
                    f.write(f"   Reasoning: {paper.get('reasoning', 'N/A')}\n")
                    if paper.get('token_usage'):
                        usage = paper['token_usage']
                        f.write(f"   Token usage: {usage.get('total_tokens', 0)} total\n")
        
        print(f"📋 Report generated: {report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="使用LLM筛选Graph + AI相关论文")
    
    # 输入输出参数
    parser.add_argument("--input", 
                        help="输入的parquet文件路径")
    parser.add_argument("--output", 
                        help="输出JSON文件路径")
    
    # 数据过滤参数
    parser.add_argument("--max_papers", type=int,
                        help="最大处理论文数量")
    parser.add_argument("--start_index", type=int, default=0,
                        help="开始处理的索引位置")
    parser.add_argument("--months", type=int,
                        help="过滤最近N个月内的论文（例如：6表示最近6个月）")
    
    # LLM配置参数
    parser.add_argument("--llm_base_url",
                        help="LLM API基础URL（优先级高于环境变量LLM_BASE_URL）")
    parser.add_argument("--llm_api_key",
                        help="LLM API密钥（优先级高于环境变量LLM_API_KEY）") 
    parser.add_argument("--llm_model", default="gpt-4",
                        help="使用的LLM模型（默认：gpt-4）")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="LLM温度参数（默认：0.1）")
    
    # 并发处理参数  
    parser.add_argument("--max_concurrent", type=int, default=32,
                        help="最大并发数量（默认32）")
    parser.add_argument("--disable_concurrent", action="store_true",
                        help="禁用并发处理，使用顺序模式")
    parser.add_argument("--rate_limit_delay", type=float, default=0.1,
                        help="并发时的速率限制延迟，单位秒（默认0.1）")
    
    # 批处理参数
    parser.add_argument("--batch_size", type=int, default=10,
                        help="批处理大小（默认10）")
    
    # 输出控制参数
    parser.add_argument("--save_all_evaluations", action="store_true",
                        help="保存所有论文的评估结果（包括被拒绝的）")
    parser.add_argument("--save_token_stats", action="store_true", 
                        help="保存详细的token使用统计文件")
    parser.add_argument("--save_progress", action="store_true",
                        help="启用checkpoint功能：每个batch后保存进度，支持断点续传")
    parser.add_argument("--save_report", action="store_true",
                        help="生成文本格式的详细报告")
    
    parser.add_argument("--resume", action="store_true",
                        help="从checkpoint恢复处理（需要同时启用--save_progress）")
    
    args = parser.parse_args()
    
    # 默认输入文件
    if not args.input:
        data_dir = "arxiv_data"
        if os.path.exists(data_dir):
            parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet') and 'cs_papers' in f]
            if parquet_files:
                args.input = os.path.join(data_dir, sorted(parquet_files)[-1])
                print(f"🔍 Using latest data file: {args.input}")
            else:
                print(f"❌ No parquet files found in {data_dir}")
                return 1
        else:
            print(f"❌ Data directory not found: {data_dir}")
            return 1
    
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        return 1
    
    try:
        # 初始化筛选器，使用命令行参数
        filter_engine = GraphAIPaperFilter(
            llm_base_url=args.llm_base_url,
            llm_api_key=args.llm_api_key,
            llm_model=args.llm_model,
            temperature=args.temperature,
            batch_size=args.batch_size,
            max_concurrent=args.max_concurrent,
            rate_limit_delay=args.rate_limit_delay,
            enable_concurrent=not args.disable_concurrent,
            save_all_evaluations=args.save_all_evaluations,
            save_token_stats=args.save_token_stats,
            save_progress=args.save_progress,
            save_report=args.save_report,
            resume_from_checkpoint=args.resume
        )
        
        # 执行筛选
        relevant_papers = filter_engine.filter_papers(
            data_file=args.input,
            output_file=args.output,
            max_papers=args.max_papers,
            start_index=args.start_index,
            months_filter=args.months
        )
        
        print(f"\n🎉 Filtering completed successfully!")
        print(f"Found {len(relevant_papers)} relevant papers in Graph + AI domains.")
        
        # 最终清理AsyncClient
        try:
            import asyncio
            # 清理异步客户端
            try:
                asyncio.run(self.async_llm.aclose())
            except Exception:
                pass
        except Exception:
            pass  # 忽略清理异常
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during filtering: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
