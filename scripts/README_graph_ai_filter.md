# Graph + AI Survey Paper Filtering Script

这个脚本使用LLM来专门识别和筛选Graph + AI领域的**综述论文**，帮助研究者快速找到领域内的高质量综述文献。

## 功能特点

- **专注综述**：专门识别Survey、Review等综述类论文，过滤掉方法论文和应用论文
- **智能识别**：通过标题关键词、摘要描述等多重特征识别综述论文
- **专业领域**：专注于Graph Neural Networks、Knowledge Graphs、GraphRAG等领域的综述
- **严格筛选**：采用"宁可漏掉，不可误判"的策略，确保筛选出的都是真正的综述
- **批量处理**：支持大规模论文数据的批量筛选
- **进度保存**：自动保存中间进度，支持断点续传
- **详细报告**：生成包含综述特征分析和Top论文的详细报告
- **Token统计**：实时跟踪API调用的token使用量和成本估算
- **成本控制**：提供详细的token使用分析和成本预估
- **并发处理**：支持多达32个并发LLM请求，大幅提升处理速度
- **智能限流**：内置速率限制和错误处理，确保API调用稳定性
- **时间过滤**：支持按时间范围筛选论文，如最近6个月内的综述
- **命令行配置**：完全基于命令行参数，无需配置文件

## 综述论文识别标准

### 目标领域
脚本专门识别以下领域的**综述论文**：
- Graph Neural Networks (GNNs) 综述
- Knowledge Graphs and AI 综述  
- Graph Foundation Models 综述
- GraphRAG 相关综述
- Graph Machine Learning 综述
- Graph-based reasoning 综述
- Multi-modal graph learning 综述
- Graph transformers 综述
- Large Language Models on graphs 综述

### 综述特征识别
脚本通过以下特征识别综述论文：

#### 标题关键词
- Survey, Review, Comprehensive Study
- Tutorial, Overview, Progress, Advances
- State-of-the-art, Comparison, Comparative Study

#### 摘要描述
- "systematic review", "comprehensive overview"
- "recent developments", "comparative analysis"
- "literature review", "field overview"
- "taxonomy", "classification", "categorization"

#### 内容特征
- 涵盖多个方法和技术
- 比较不同技术的优缺点
- 总结领域发展历程
- 提供分类框架或taxonomy

## 时间过滤功能

脚本支持按时间范围筛选论文，帮你专注于最新的研究进展。

### 时间过滤示例
- `--months 1`: 只分析最近1个月内的论文
- `--months 3`: 只分析最近3个月内的论文  
- `--months 6`: 只分析最近6个月内的论文
- `--months 12`: 只分析最近12个月内的论文
- 不使用`--months`参数: 分析所有论文

### 数据显示
脚本会在开始处理前显示：
- 文件中的总论文数量
- 时间过滤后的论文数量
- 最终要分析的论文数量

### 示例输出
```
📖 Loading papers from: arxiv_data/cs_papers_6months_20250812_002744.parquet
📊 Total papers in file: 174,966
⏰ Time filtering: 6 months
   Cutoff date: 2025-02-12
   Before filtering: 174,966 papers
   After filtering: 102,859 papers
   Filtered out: 72,107 papers
📋 Final paper count to analyze: 102,859
```

## 安装和设置

### 1. 环境变量配置

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-base-url"  # 可选，如果使用自定义API端点
```

### 2. 依赖项

脚本使用项目现有的依赖项，无需额外安装。

## 使用方法

### 环境变量设置（必需）

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-base-url"  # 可选，如果使用自定义API端点
```

### 基本用法

```bash
# 使用默认设置筛选最新的论文数据
python scripts/filter_graph_ai_papers.py

# 指定输入文件
python scripts/filter_graph_ai_papers.py --input arxiv_data/cs_papers_6months_20250812_002744.parquet

# 限制处理论文数量（用于测试）
python scripts/filter_graph_ai_papers.py --max_papers 50

# 过滤最近6个月的论文
python scripts/filter_graph_ai_papers.py --months 6 --max_papers 100

# 过滤最近3个月的论文，限制50篇
python scripts/filter_graph_ai_papers.py --months 3 --max_papers 50

# 从指定位置开始处理（用于断点续传）
python scripts/filter_graph_ai_papers.py --start_index 100 --max_papers 50

# 调整并发设置（16个并发，延迟0.2秒）
python scripts/filter_graph_ai_papers.py --max_papers 100 --max_concurrent 16 --rate_limit_delay 0.2

# 禁用并发，使用顺序处理
python scripts/filter_graph_ai_papers.py --max_papers 50 --disable_concurrent

# 指定LLM模型和参数
python scripts/filter_graph_ai_papers.py --llm_model gpt-4-turbo --temperature 0.2 --months 6
```

### 参数说明

#### 输入输出参数
- `--input`: 输入的parquet文件路径（可选，默认使用最新的数据文件）
- `--output`: 输出JSON文件路径（可选，默认自动生成时间戳文件名）

#### 数据过滤参数
- `--max_papers`: 最大处理论文数量（可选，用于测试或分批处理）
- `--start_index`: 开始处理的索引位置（可选，用于断点续传）
- `--months`: 过滤最近N个月内的论文（可选，例如：6表示最近6个月）

#### LLM配置参数
- `--llm_base_url`: LLM API基础URL（可选，优先级高于环境变量LLM_BASE_URL）
- `--llm_api_key`: LLM API密钥（可选，优先级高于环境变量LLM_API_KEY）
- `--llm_model`: 使用的LLM模型（可选，默认：gpt-4）
- `--temperature`: LLM温度参数（可选，默认：0.1）

#### 并发处理参数
- `--max_concurrent`: 最大并发数量（可选，默认32）
- `--disable_concurrent`: 禁用并发处理，使用顺序模式（可选）
- `--rate_limit_delay`: 并发时的速率限制延迟，单位秒（可选，默认0.1）
- `--batch_size`: 批处理大小（可选，默认10）

### 测试功能

```bash
# 创建测试数据并运行干测试
python scripts/test_graph_ai_filter.py

# 仅运行干测试（不调用LLM）
python scripts/test_graph_ai_filter.py --dry-run

# 仅创建测试数据
python scripts/test_graph_ai_filter.py --create-test-data

# 使用测试数据运行完整流程
python scripts/filter_graph_ai_papers.py --input arxiv_data/test_papers.parquet --max_papers 3
```

## 输出文件

脚本会生成以下文件：

1. **主要输出文件**：`graph_ai_papers_YYYYMMDD_HHMMSS.json`
   - 包含筛选出的相关论文和元数据

2. **完整评估结果**：`*_all_evaluations.json`
   - 包含所有论文的评估详情

3. **Token统计文件**：`*_token_stats.json`
   - 详细的token使用统计和成本分析

4. **统计报告**：`*_report.txt`
   - 人类可读的筛选统计、Top论文列表和token使用分析

5. **进度文件**：`*_progress_N.json`
   - 中间进度保存文件

## 评估标准

LLM会对每篇论文进行三个维度的评分（1-10分）：

1. **领域相关性** (1-10分)：论文与Graph + AI领域的相关程度
   - 9-10分：Graph + AI核心领域的综述
   - 7-8分：相关领域的综述
   - 1-6分：不相关或非综述论文

2. **综述特征** (1-10分)：论文是否具备综述论文特征
   - 9-10分：明显的综述论文，标题含Survey/Review等
   - 7-8分：综述性质明显
   - 1-6分：非综述论文

3. **综述质量** (1-10分)：综述论文的质量和价值
   - 9-10分：全面深入的领域综述
   - 7-8分：质量较高的综述
   - 1-6分：综述质量有限或非综述

**严格筛选规则**：
- 必须同时满足"领域相关"和"确实是综述"才能被标记为目标论文
- 纯粹的方法论文、应用论文一律排除
- 只有综合评分 ≥ 7.0 且 is_survey = true 的论文才会被选中

## 示例输出

```json
{
  "metadata": {
    "total_evaluated": 100,
    "relevant_found": 15,
    "success_rate": 0.15,
    "evaluation_time": "2025-08-12T10:30:00",
    "token_usage": {
      "cost_estimate": {
        "total_cost_usd": 2.4567,
        "cost_per_paper": 0.0246
      },
      "efficiency_metrics": {
        "total_api_calls": 100,
        "avg_total_tokens": 850.5
      }
    }
  },
  "papers": [
    {
      "arxiv_id": "2401.12345",
      "title": "A Comprehensive Survey of Graph Neural Networks",
      "relevance_score": 9,
      "paper_type_score": 10,
      "importance_score": 8,
      "overall_score": 9.0,
      "is_target_paper": true,
      "is_survey": true,
      "reasoning": "明显的综述论文，标题包含Survey，摘要描述系统性回顾",
      "survey_indicators": ["标题含Survey", "摘要提到comprehensive survey", "系统性回顾特征"],
      "key_topics": ["Graph Neural Networks", "Survey", "Node Classification"],
      "token_usage": {
        "prompt_tokens": 750,
        "completion_tokens": 120,
        "total_tokens": 870,
        "model": "gpt-4"
      }
    }
  ]
}
```

## 并发处理功能

脚本支持高效的并发处理，可以显著提升大规模论文筛选的速度。

### 并发设置
- **默认并发数**: 32个同时进行的LLM请求
- **速率限制**: 每个请求间隔0.1秒，避免API限制
- **批处理**: 按批次处理论文，避免内存问题
- **错误处理**: 自动处理并发请求中的异常情况

### 性能对比
- **顺序处理**: 每篇论文约2-3秒（包括0.5秒延迟）
- **并发处理**: 32篇论文同时处理，整体速度提升约10-20倍
- **实际效果**: 1000篇论文从45分钟缩短至3-5分钟

### 并发优化建议
1. **API限制**: 根据你的API provider的限制调整并发数
2. **网络环境**: 网络不稳定时可降低并发数（如16或8）
3. **成本控制**: 并发虽快但会增加短时间内的API调用成本
4. **测试先行**: 建议先用小批量测试最佳并发设置

### 使用示例
```bash
# 高速模式（适合稳定API和网络环境）
python scripts/filter_graph_ai_papers.py --max_concurrent 32 --rate_limit_delay 0.1

# 稳定模式（适合有API限制的环境）
python scripts/filter_graph_ai_papers.py --max_concurrent 16 --rate_limit_delay 0.2

# 保守模式（适合网络不稳定或严格限制的环境）
python scripts/filter_graph_ai_papers.py --max_concurrent 8 --rate_limit_delay 0.5

# 调试模式（完全顺序处理，便于调试）
python scripts/filter_graph_ai_papers.py --disable_concurrent
```

## Token使用和成本分析

脚本会自动跟踪以下token使用信息：

### Token统计
- **输入Token**：发送给LLM的prompt tokens
- **输出Token**：LLM生成的completion tokens  
- **总Token数**：输入+输出token总和
- **平均Token数**：每次API调用的平均token使用量

### 成本估算
基于主流LLM模型定价自动估算：
- **GPT-4**: 输入$0.03/1k tokens, 输出$0.06/1k tokens
- **GPT-4 Turbo**: 输入$0.01/1k tokens, 输出$0.03/1k tokens  
- **GPT-3.5 Turbo**: 输入$0.0015/1k tokens, 输出$0.002/1k tokens

### 实时监控
- 每处理一批论文显示当前token使用情况
- 最终报告包含完整的成本分析
- 单独的token统计文件用于详细分析

## 注意事项

1. **API费用**：脚本会调用LLM API，实时显示token使用和成本估算
2. **处理速度**：并发模式下速度大幅提升，但要注意API限制
3. **断点续传**：如果处理中断，可使用 `--start_index` 参数从指定位置继续
4. **批量大小**：默认每10篇论文保存一次进度，可在配置文件中调整
5. **成本预估**：建议先用小批量数据测试，预估成本后再处理大规模数据
6. **并发调优**：根据API provider和网络情况调整并发数和延迟参数

## 配置文件示例

```json
{
  "llm_base_url": null,
  "llm_api_key": null, 
  "llm_model": "gpt-4",
  "temperature": 0.1,
  "batch_size": 10,
  "output_dir": "arxiv_data/filtered_papers",
  "max_concurrent": 32,
  "rate_limit_delay": 0.1,
  "enable_concurrent": true
}
```

## 故障排除

1. **LLM API错误**：检查API密钥和端点配置
2. **文件不存在**：确认输入文件路径正确
3. **内存不足**：使用 `--max_papers` 参数分批处理
4. **网络超时**：检查网络连接和API端点可用性