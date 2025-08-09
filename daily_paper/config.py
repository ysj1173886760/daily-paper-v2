import yaml
from pydantic import BaseModel


class Config(BaseModel):
    arxiv_topic_list: list[str] = []
    arxiv_search_offset: int = 0
    arxiv_search_limit: int = 50

    meta_file_path: str = "data/test.parquet"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    feishu_webhook_url: str = ""
    
    # Daily Summary飞书推送配置
    daily_summary_feishu_webhook_url: str = ""  # 每日汇总独立的飞书webhook URL

    # LLM论文过滤相关配置
    enable_llm_filter: bool = False  # 是否启用LLM过滤器
    user_interested_content: str = ""  # 用户感兴趣的论文内容描述

    # 论文分析模板配置
    analysis_template: str = "simple"  # 分析模板名称，可选值: "simple", "v1", "v2"

    # RSS发布配置
    rss_site_url: str = "https://your-username.github.io/daily-papers-site"
    rss_feed_title: str = "Daily AI Papers"
    rss_feed_description: str = (
        "Latest papers in AI research - RAG, Knowledge Graph, and more"
    )
    rss_custom_tag: str = ""  # 自定义标签，用于替代按领域分类

    # GitHub Pages部署配置
    github_token: str = ""  # GitHub Personal Access Token
    github_repo_owner: str = ""  # GitHub用户名
    github_repo_name: str = "daily-papers-site"  # 网站仓库名
    
    # 发布选项配置
    enable_feishu_push: bool = False  # 是否启用飞书推送
    enable_rss_publish: bool = False  # 是否启用RSS发布

    # 每日汇总工作流配置
    daily_summary_enabled: bool = False  # 是否启用每日汇总工作流
    daily_summary_tracker_file: str = "data/report_tracker.json"  # 推送跟踪文件路径
    daily_summary_max_days: int = 7  # 批量模式下最多处理的天数
    daily_summary_recommendation_count: int = 3  # 推荐论文数量
    daily_summary_default_start_days_ago: int = 7  # 默认开始处理几天前的数据
    daily_summary_skip_no_paper_dates: bool = True  # 跳过没有论文的日期
    daily_summary_continue_on_push_failure: bool = False # 推送失败时继续处理下一天

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
