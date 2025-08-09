# arXiv 论文统计脚本集合

这个目录包含了用于统计和分析arXiv论文数据的脚本工具。

## 🔧 脚本列表

### 1. `stats_cs_ai_papers.py` - 单分类论文统计 ⭐️ 主要工具

统计指定cs分类最近N天的论文数量，提供详细的统计分析。

#### 功能特点
- ✅ 支持18种主要cs分类统计
- ✅ 详细统计信息：平均值、中位数、P99、最大值、最小值、标准差
- ✅ 按日期分组显示论文详情
- ✅ 活跃日期统计和论文数量趋势分析
- ✅ 支持CSV格式数据导出
- ✅ 中文友好的日期显示格式

#### 使用方法
```bash
# 统计cs.AI最近7天（默认）
python scripts/arxiv/stats_cs_ai_papers.py

# 统计cs.IR分类的论文
python scripts/arxiv/stats_cs_ai_papers.py --category cs.IR

# 统计cs.CV最近14天
python scripts/arxiv/stats_cs_ai_papers.py --days 14 --category cs.CV

# 列出所有支持的分类
python scripts/arxiv/stats_cs_ai_papers.py --list-categories

# 统计并导出到CSV文件
python scripts/arxiv/stats_cs_ai_papers.py --export cs_stats.csv

# 显示详细日志
python scripts/arxiv/stats_cs_ai_papers.py --verbose --days 5 --max-results 100
```

### 2. `quick_cs_overview.py` - 快速多分类概览

快速统计主要cs分类的论文数量概览，适合获取整体趋势。

#### 使用方法
```bash
# 统计最近7天的主要分类概览
python scripts/arxiv/quick_cs_overview.py --days 7

# 统计最近30天（每分类最多获取800篇）
python scripts/arxiv/quick_cs_overview.py --days 30 --max-results 800
```

### 3. `batch_cs_stats.py` - 批量完整统计

批量统计所有cs分类的详细数据，耗时较长但数据最完整。

#### 使用方法
```bash
# 批量统计所有分类最近30天
python scripts/arxiv/batch_cs_stats.py --days 30

# 导出详细数据到CSV
python scripts/arxiv/batch_cs_stats.py --export detailed_report.csv

# 调整参数减少API请求
python scripts/arxiv/batch_cs_stats.py --days 7 --max-results 500 --delay 3
```

### 4. `monthly_cs_estimate.py` - 月度数据估算

基于一周真实数据估算月度统计，快速获得长期趋势。

#### 使用方法
```bash
# 基于最近7天数据估算30天统计
python scripts/arxiv/monthly_cs_estimate.py
```

### 5. `show_cs_monthly_stats.py` - 月度统计展示

展示基于已知数据的月度统计报告，无需API调用。

#### 使用方法
```bash
# 显示预计算的月度统计报告
python scripts/arxiv/show_cs_monthly_stats.py
```

## 🎯 使用建议

### 场景 1: 快速了解单个分类
```bash
python scripts/arxiv/stats_cs_ai_papers.py --category cs.AI --days 7
```

### 场景 2: 获取多分类概览
```bash
python scripts/arxiv/quick_cs_overview.py --days 7
```

### 场景 3: 详细分析和导出数据  
```bash
python scripts/arxiv/stats_cs_ai_papers.py --category cs.LG --days 14 --export ml_analysis.csv
```

### 场景 4: 月度趋势分析
```bash
python scripts/arxiv/show_cs_monthly_stats.py
```

## 📊 支持的cs分类

当前支持以下18个主要cs分类：

| 分类 | 名称 | 分类 | 名称 |
|------|------|------|------|
| `cs.AI` | Artificial Intelligence | `cs.IR` | Information Retrieval |
| `cs.LG` | Machine Learning | `cs.CL` | Computation and Language |
| `cs.CV` | Computer Vision | `cs.DB` | Databases |
| `cs.CR` | Cryptography and Security | `cs.DC` | Distributed Computing |
| `cs.SE` | Software Engineering | `cs.HC` | Human-Computer Interaction |
| `cs.RO` | Robotics | `cs.NE` | Neural and Evolutionary Computing |
| `cs.DS` | Data Structures and Algorithms | `cs.NI` | Networking |
| `cs.OS` | Operating Systems | `cs.PL` | Programming Languages |
| `cs.GT` | Game Theory | `cs.SY` | Systems and Control |

## ⚡ 性能说明

- **单分类统计**: 约5-10秒（100-500篇论文）
- **多分类概览**: 约1-2分钟（10个分类）
- **批量完整统计**: 约5-15分钟（18个分类，取决于数据量）
- **月度估算**: 约1-3分钟（基于一周数据）

## ⚠️ 注意事项

1. **API限制**: arXiv API有请求频率限制，脚本已内置延迟机制
2. **数据时效**: 统计基于论文的更新时间，可能与发布时间略有差异
3. **网络依赖**: 需要稳定的网络连接访问arXiv API
4. **虚拟环境**: 建议在项目虚拟环境中运行：`source .venv/bin/activate`

## 🚀 快速开始

```bash
# 激活虚拟环境
source .venv/bin/activate

# 查看支持的分类
python scripts/arxiv/stats_cs_ai_papers.py --list-categories

# 快速统计AI分类最近一周
python scripts/arxiv/stats_cs_ai_papers.py --category cs.AI --days 7

# 获取多分类概览
python scripts/arxiv/quick_cs_overview.py --days 7
```

## 📝 输出格式

脚本支持以下输出格式：
- **控制台输出**: 带emoji的友好显示格式
- **CSV导出**: 适合进一步数据分析
- **详细日志**: 使用`--verbose`参数获取调试信息

## 🔧 故障排除

### 常见问题

1. **ModuleNotFoundError**: 请确保在项目虚拟环境中运行
2. **网络超时**: 检查网络连接或减少`--max-results`参数
3. **API限制**: 脚本已内置3秒延迟，如仍有问题可增加`--delay`参数
4. **数据为空**: 某些分类在特定时间段可能没有新论文，属正常情况

### 调试技巧

```bash
# 使用详细日志模式
python scripts/arxiv/stats_cs_ai_papers.py --verbose --category cs.AI --days 3

# 限制数据量进行快速测试
python scripts/arxiv/stats_cs_ai_papers.py --category cs.AI --days 1 --max-results 50
```

---
*更新时间: 2025年8月*