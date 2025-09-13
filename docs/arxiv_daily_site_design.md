# ArXiv 每日站点功能设计

## 目标
- 每日自动获取“昨天”新增的 arXiv CS 论文，筛选 cs.AI 与 cs.IR。
- 对摘要进行 LLM 增强：关键词提取与中英对照翻译。
- 生成一周内的滑动展示站点，便于快速浏览学术进展。

## 数据流与模块
1) 获取元数据
- 复用 `scripts/arxiv/bulk_cs_metadata.py` 的 OAI-PMH 能力，新增按日范围抓取（from=昨天 00:00, until=昨天 23:59）。
- 过滤 `cs_categories` 包含 `cs.AI` 或 `cs.IR` 的记录。

2) LLM 增强
- 使用 `daily_paper.utils.call_llm` 调用配置的 LLM：
  - 产出字段：`keywords`(5–10 个英文短语)、`title_zh`、`abstract_zh`。
  - 提示词要点：保持学术名词、去掉冗余、关键词用逗号分隔。

3) 持久化与聚合
- 原始数据（昨日）保存：`arxiv_data/daily/YYYY-MM-DD.parquet`
- 增强数据保存：`data/ai_ir_daily/YYYY-MM-DD_enriched.parquet`
- 导出站点 JSON（仅近 7 天）：`public/arxiv-daily/YYYY-MM-DD.json`

4) 站点生成与发布
- 生成静态资源到 `public/`：
  - 单日页面输出到 `public/posts/`（文件名示例：`YYYY-MM-DD-<arxiv_id>.html`）。
  - 可选导出聚合 JSON 到 `public/arxiv-daily/YYYY-MM-DD.json`（如需 API/前端异步读取）。
- 部署复用 `daily_paper/nodes/deploy_github_node.py`，通过 GitHub API 推送 `public/` 下文件到站点仓库。

## 数据结构（增强后）
- `arxiv_id, title, authors, abstract, cs_categories, date_submitted`
- `keywords: List[str], title_zh: str, abstract_zh: str, enriched_at`

## 配置与运行
- 复用 `config/test.yaml` 的 LLM 配置键：`llm_base_url, llm_api_key, llm_model`。
- 新增脚本（建议）：`scripts/arxiv/daily_ingest_ai_ir.py --date YYYY-MM-DD`，串联上述步骤。

## 部署方式（参考 DeployGitHubNode）
- 输出接口：将生成页面写入 `public/posts/` 并在共享存储设置 `html_files`（每项包含 `filename`）。
- 节点行为：`DeployGitHubNode` 会读取 `shared['html_files']` 和 `public/rss.xml`，比较远端与本地内容后，批量 push 到目标仓库的 `main` 分支对应路径（形如 `public/posts/<filename>`）。
- 配置项：
  - `github_token`: GitHub Personal Access Token（只需 `contents:write` 与 `repo`）。
  - `github_repo_owner`: 站点仓库拥有者。
  - `github_repo_name`: 站点仓库名（默认为 `daily-papers-site`）。
- 说明：若需同时推送 `public/arxiv-daily/*.json`，可在 `DeployGitHubNode._deploy_by_api_push` 中加入该目录扫描与 push（或将 JSON 以“伪 HTML 文件”形式加入 `html_files` 列表以复用当前流程）。

## 调度与重试
- 本地 cron：`0 8 * * *  source .venv/bin/activate && python scripts/arxiv/daily_ingest_ai_ir.py --date $(date -v-1d +%F)`
- GitHub Actions：每日定时，失败告警；幂等基于 `arxiv_id + date` 去重。

## 错误与限流
- OAI 请求指数退避（脚本已支持），LLM 调用失败重试最多 3 次并记录。
- 缺字段样本跳过但记录日志；整体失败不影响既有页面。
