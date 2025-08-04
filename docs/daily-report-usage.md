# 日报功能使用说明

## 功能概述

昨日论文报告功能可以自动生成前一天的论文分析报告，包括：
- 📊 论文统计概览
- 🔍 智能趋势分析  
- ⭐ 推荐论文列表
- 📋 完整论文清单
- 🤖 自动推送到飞书

## 快速开始

### 1. 独立测试

使用提供的测试脚本：

```bash
# 生成昨日报告（默认）
python test_daily_report.py

# 指定特定日期
python test_daily_report.py --date 2025-01-15

# 使用不同配置文件
python test_daily_report.py --config config/kg.yaml
```

### 2. 编程调用

```python
from daily_paper.config import Config
from daily_paper.flow.daily_report_flow import run_daily_report_with_config
from daily_paper.utils.call_llm import init_llm
from daily_paper.utils.feishu_client import init_feishu

# 加载配置
config = Config.from_yaml("config/rag.yaml")

# 初始化服务
init_llm(config.llm_base_url, config.llm_api_key, config.llm_model)
init_feishu(config.feishu_webhook_url)

# 运行日报流程
result = run_daily_report_with_config(config)

# 查看结果
papers_count = len(result.get("yesterday_papers", []))
push_success = result.get("push_result", {}).get("success", False)
print(f"处理了{papers_count}篇论文，推送{'成功' if push_success else '失败'}")
```

## 工作流程

### 节点架构

1. **FetchYesterdayPapersNode**: 获取昨日论文
   - 从PaperMetaManager获取指定日期的论文
   - 过滤出有有效summary的论文

2. **AnalyzeAndRecommendPapersNode**: 分析并推荐
   - 调用LLM对论文进行综合分析
   - 生成趋势分析和推荐列表
   - 包含智能重试和回退机制

3. **PushDailyReportToFeishuNode**: 格式化并推送
   - 将分析结果格式化为markdown报告
   - 推送到飞书群聊

### 数据流

```
论文数据库 → 昨日论文 → LLM分析 → 格式化报告 → 飞书推送
```

## 报告格式

生成的日报包含以下部分：

```markdown
# 📊 AI论文日报 - 2025年1月15日

## 📈 今日概览
- **论文总数**: 8篇
- **推荐论文**: 3篇  
- **主要领域**: RAG, Knowledge Graph
- **热点话题**: 多模态检索, 知识图谱推理

## 🔍 趋势分析
[LLM生成的综合分析...]

## ⭐ 推荐论文

### 1. 论文标题
**推荐理由**: [具体推荐理由]
**核心亮点**: 亮点1 | 亮点2 | 亮点3
**作者**: 第一作者
**分类**: cs.AI
**链接**: https://arxiv.org/abs/...

## 📋 完整论文列表
[所有论文的简要信息]
```

## 配置选项

可以通过配置文件调整以下参数：

```yaml
# 日报配置（可选）
daily_report_recommendation_count: 3  # 推荐论文数量
```

## 错误处理

系统包含多层错误处理机制：

1. **无论文处理**: 如果指定日期没有论文，优雅结束
2. **LLM失败回退**: 如果LLM分析失败，提供基础统计信息  
3. **推送失败回退**: 如果推送失败，生成简化报告重试

## 技术特性

- ✅ 基于PocketFlow框架的节点化设计
- ✅ 智能LLM分析和推荐算法
- ✅ 完善的错误处理和重试机制
- ✅ 灵活的日期选择（默认昨天）
- ✅ 结构化的报告格式
- ✅ 飞书群聊自动推送

## 日志输出

运行时会输出详细的执行日志：

```
2025-01-16 09:00:01 - INFO - 开始获取 2025年1月15日 的论文
2025-01-16 09:00:02 - INFO - 获取到 8 篇论文，其中 8 篇有有效摘要
2025-01-16 09:00:03 - INFO - 开始分析 8 篇论文并生成推荐
2025-01-16 09:00:15 - INFO - 论文分析和推荐完成
2025-01-16 09:00:16 - INFO - 开始格式化日报并推送到飞书
2025-01-16 09:00:17 - INFO - 日报已成功推送到飞书
```

## 后续扩展

当前实现为MVP版本，后续可以扩展：

- 支持RSS推送
- 可配置的推荐算法
- 历史趋势对比
- 自定义报告模板  
- 多语言支持