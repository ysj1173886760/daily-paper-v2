# 每日汇总工作流使用指南

## 🎯 功能概述

每日汇总工作流已集成到主程序中，用于处理历史未推送的日报，确保每天的论文分析都能及时推送到飞书群组。

## 🚀 快速开始

### 1. 启用功能

在配置文件中启用每日汇总功能：

**config/rag.yaml** (RAG论文)
```yaml
daily_summary_enabled: true
daily_summary_tracker_file: "data/rag_report_tracker.json"
```

**config/kg.yaml** (知识图谱论文)  
```yaml
daily_summary_enabled: true
daily_summary_tracker_file: "data/kg_report_tracker.json"
```

### 2. 基本使用

```bash
# 完整流程（处理新论文 + 推送 + 每日汇总）
python main.py --config_path config/rag.yaml --mode full

# 仅发布模式（推送现有论文 + 每日汇总）  
python main.py --config_path config/rag.yaml --mode publish

# 仅处理新论文（不会触发每日汇总）
python main.py --config_path config/rag.yaml --mode summary
```

## ⚙️ 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `daily_summary_enabled` | false | 是否启用每日汇总功能 |
| `daily_summary_tracker_file` | - | 推送状态跟踪文件路径 |
| `daily_summary_max_days` | 7 | 批量模式最多处理天数 |
| `daily_summary_recommendation_count` | 3 | 每日推荐论文数量 |

## 🔄 工作原理

1. **获取待处理日期**: 从跟踪文件中找到下一个未推送的日期
2. **获取论文数据**: 复用现有的 `FetchYesterdayPapersNode` 
3. **分析和推荐**: 复用现有的 `AnalyzeAndRecommendPapersNode`
4. **推送到飞书**: 复用现有的 `PushDailyReportToFeishuNode`
5. **更新状态**: 记录推送结果，确保幂等性

## 📅 定时任务设置

将以下内容添加到 crontab（`crontab -e`）：

```bash
# 每天上午9点运行RAG论文完整流程（包含每日汇总）
0 9 * * * cd /path/to/daily-paper-v2 && python main.py --config_path config/rag.yaml --mode full

# 每天上午10点运行知识图谱论文完整流程（包含每日汇总）
0 10 * * * cd /path/to/daily-paper-v2 && python main.py --config_path config/kg.yaml --mode full

# 每天下午6点仅运行发布模式（推送现有论文 + 每日汇总）
0 18 * * * cd /path/to/daily-paper-v2 && python main.py --config_path config/rag.yaml --mode publish
```

## 🛟 故障排除

### 功能未启用
如果看到日志 `每日汇总功能未启用，跳过`，说明配置文件中未启用该功能。

**解决方案**: 在配置文件中添加 `daily_summary_enabled: true`

### 没有论文数据
系统会自动标记该日期为"无论文状态"，避免重复尝试。日志会显示类似：
```
WARNING - 2025年8月2日 没有找到有效论文，标记为无论文状态
```

### 推送失败
推送失败会被记录，可以重新运行工作流来重试失败的日期。

### 无限循环处理同一日期
系统有防循环机制，如果连续处理同一日期且失败，会自动停止避免无限循环。

## 🔍 数据文件

- **跟踪文件**: `data/rag_report_tracker.json` / `data/kg_report_tracker.json`
  - 记录每日推送状态和历史
  - 确保工作流的幂等性

- **论文数据**: 来自现有的 `meta_file_path` 配置
  - RAG: `data/daily_papers.parquet`
  - KG: `data/daily_papers_kg.parquet`

## ✨ 特性

- ✅ **幂等性**: 不会重复处理已推送的日期
- ✅ **复用现有组件**: 最大化复用现有的节点和配置
- ✅ **灵活配置**: 支持不同领域的独立配置
- ✅ **错误处理**: 优雅处理各种异常情况
- ✅ **状态跟踪**: 完整的推送历史记录