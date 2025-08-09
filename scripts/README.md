# Scripts 目录

这个目录包含了用于管理 Daily Paper 系统的实用脚本。

## 脚本列表

### 1. `arxiv/` - arXiv论文统计脚本集合 ⭐️

专门用于统计和分析arXiv论文数据的脚本工具集，包含5个核心脚本：

- **`stats_cs_ai_papers.py`** - 单分类详细统计（主要工具）
- **`quick_cs_overview.py`** - 快速多分类概览  
- **`batch_cs_stats.py`** - 批量完整统计
- **`monthly_cs_estimate.py`** - 月度数据估算
- **`show_cs_monthly_stats.py`** - 月度统计展示

#### 快速开始
```bash
# 查看支持的分类
python scripts/arxiv/stats_cs_ai_papers.py --list-categories

# 统计cs.AI最近7天
python scripts/arxiv/stats_cs_ai_papers.py --category cs.AI

# 快速多分类概览
python scripts/arxiv/quick_cs_overview.py --days 7

# 详细月度统计报告
python scripts/arxiv/show_cs_monthly_stats.py
```

#### 功能特点
- ✅ 支持18种主要cs分类统计
- ✅ 详细统计信息：avg、p99、max、标准差等
- ✅ 多种统计模式：单分类、多分类、批量分析
- ✅ 支持CSV导出和数据可视化
- ✅ 中文友好显示和完整文档

📖 **详细文档**: [scripts/arxiv/README.md](arxiv/README.md)

### 2. `quick_set_template.py` - 快速设置模板

最简单的设置现有数据模板的脚本，适合日常使用。

#### 使用方法

```bash
# 查看当前模板使用统计
python scripts/quick_set_template.py --stats

# 为所有未设置模板的论文设置 v2 模板
python scripts/quick_set_template.py v2

# 为指定数据文件设置 v1 模板
python scripts/quick_set_template.py v1 data/rag.parquet

# 查看可用模板
python scripts/quick_set_template.py
```

#### 功能特点
- ✅ 只设置未设置模板的论文（不会覆盖已有的）
- ✅ 自动显示操作前后的统计信息
- ✅ 支持指定数据文件
- ✅ 简单易用的命令行界面

### 2. `set_template_for_existing_data.py` - 高级模板设置

功能更全面的模板管理脚本，支持多种设置方式。

#### 使用方法

```bash
# 使用配置文件设置模板
python scripts/set_template_for_existing_data.py --config config/rag.yaml --template v2

# 按日期范围设置模板
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --template v1 \
    --start-date 2024-01-01 \
    --end-date 2024-06-30

# 自动分析摘要内容推断模板类型
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --auto-analyze

# 试运行（不实际修改数据）
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --template v2 \
    --dry-run

# 只显示统计信息
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --stats-only
```

#### 功能特点
- ✅ 支持配置文件和直接指定数据文件
- ✅ 按日期范围过滤论文
- ✅ 自动分析摘要内容推断模板类型
- ✅ 试运行模式
- ✅ 详细的统计信息显示
- ✅ 灵活的命令行选项

## 使用场景

### 场景 1: 初次设置现有数据
如果你有一批现有的论文数据，还没有设置模板信息：

```bash
# 查看当前状态
python scripts/quick_set_template.py --stats

# 为所有论文设置默认模板
python scripts/quick_set_template.py v2
```

### 场景 2: 按时间段设置不同模板
如果你想为不同时期的论文设置不同的模板：

```bash
# 2024年上半年使用 v1 模板
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --template v1 \
    --start-date 2024-01-01 \
    --end-date 2024-06-30

# 2024年下半年使用 v2 模板  
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --template v2 \
    --start-date 2024-07-01 \
    --end-date 2024-12-31
```

### 场景 3: 智能分析设置
让脚本自动分析摘要内容来推断模板类型：

```bash
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --auto-analyze
```

### 场景 4: 谨慎操作
在实际修改前先试运行：

```bash
python scripts/set_template_for_existing_data.py \
    --data-file data/daily_papers.parquet \
    --template v2 \
    --dry-run
```

## 注意事项

1. **备份数据**: 在运行脚本前建议备份重要的数据文件
2. **权限检查**: 确保脚本有读写数据文件的权限
3. **模板验证**: 脚本会自动验证模板名称是否存在
4. **增量更新**: 脚本默认只更新未设置模板的论文，不会覆盖已有设置

## 可用模板

当前系统支持以下模板：

- `simple`: 简单摘要模板，生成基础的论文介绍
- `v1`: 经典论文分析模板，包含8个核心维度的分析
- `v2`: 深度结构化论文分析模板，包含11个维度的详细分析

## 故障排除

### 常见问题

1. **找不到数据文件**
   ```
   错误: 数据文件不存在: data/daily_papers.parquet
   ```
   解决方案: 检查文件路径是否正确，或使用 `--config` 指定配置文件

2. **模板不存在**
   ```
   错误: 模板 'v3' 不存在
   ```
   解决方案: 使用 `python scripts/quick_set_template.py` 查看可用模板

3. **权限错误**
   ```
   Permission denied: data/daily_papers.parquet
   ```
   解决方案: 检查文件权限，确保脚本可以读写数据文件

## 开发者说明

如需修改或扩展脚本功能，请注意：

1. 脚本位于 `scripts/` 目录下
2. 使用 `sys.path.insert(0, str(project_root))` 来导入项目模块
3. 遵循现有的日志和错误处理模式
4. 更新此 README 文档说明新功能

## 相关文档

- [模板系统文档](../daily_paper/templates/README.md)
- [数据管理文档](../daily_paper/utils/data_manager.py)
- [配置文件说明](../config/README.md)