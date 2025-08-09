# Daily Paper V2

Daily Paper Processing System - 基于PocketFlow框架的自动化学术论文处理系统

## 功能特性

- 📄 **论文获取**: 从arXiv自动获取最新论文
- 🧠 **智能分析**: 使用LLM生成论文摘要和分析
- 📱 **飞书推送**: 自动推送论文到飞书群聊
- 📊 **每日汇总**: 生成每日论文汇总报告
- 🌐 **RSS发布**: 支持RSS订阅和GitHub Pages部署
- 📝 **模板系统**: 支持多种分析模板(v1, v2, simple, fast_analysis)

## 快速开始

```bash
# 基本使用
python main.py --config_path config/rag.yaml

# 使用其他配置
python main.py --config_path config/kg.yaml
```

## 配置说明

系统完全通过配置文件控制，支持以下主要功能：

### 基础配置
```yaml
# 论文源配置
arxiv_topic_list: ["RAG", "Retrieval-Augmented Generation"]
arxiv_search_limit: 50

# LLM配置
llm_base_url: "your-llm-endpoint"
llm_api_key: "your-api-key"
llm_model: "your-model"

# 分析模板
analysis_template: "v2"  # 可选: v1, v2, simple, fast_analysis
```

### 推送配置
```yaml
# 飞书推送
enable_feishu_push: true
feishu_webhook_url: "your-feishu-webhook"

# RSS发布
enable_rss_publish: true
rss_site_url: "https://your-username.github.io/daily-papers-site"
rss_feed_title: "Daily AI Papers"
```

### 每日汇总配置
```yaml
# 每日汇总功能
daily_summary_enabled: true
daily_summary_feishu_webhook_url: "separate-webhook-for-summary"  # 可选独立群
daily_summary_max_days: 7
daily_summary_recommendation_count: 3
daily_summary_skip_no_paper_dates: true
```

## 可用配置文件

- `config/rag.yaml` - RAG相关论文
- `config/kg.yaml` - 知识图谱相关论文  
- `config/test.yaml` - 测试配置

## 模块说明

### 论文处理流程
1. **获取论文** (FetchPapersNode)
2. **过滤重复** (FilterExistingPapersNode)  
3. **LLM过滤** (FilterIrrelevantPapersNode) - 可选
4. **生成摘要** (ProcessPapersV2Node)
5. **飞书推送** (PushToFeishuNode) - 可选
6. **RSS发布** (GenerateHTMLNode + PublishRSSNode) - 可选
7. **每日汇总** (DailySummaryFlow) - 可选

### 每日汇总特性
- 自动跳过无论文的日期
- 智能日期推进逻辑
- 支持独立飞书群推送
- 批量处理历史未推送日期
- 完整的错误处理和重试机制

## 数据存储

- 论文元数据: Parquet文件格式
- 推送跟踪: JSON文件记录推送状态
- 配置驱动: 所有行为通过YAML配置控制

## 项目架构

基于PocketFlow框架的"Graph + Shared Store"模式：
- **节点(Node)**: 处理具体任务
- **流程(Flow)**: 连接节点形成工作流
- **共享存储**: 节点间数据交换
- **批处理**: 支持大数据量处理

更多详细信息请查看 `CLAUDE.md` 和 `docs/` 目录。