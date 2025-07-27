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

    # GitHub Pages部署配置
    github_token: str = ""  # GitHub Personal Access Token
    github_repo_owner: str = ""  # GitHub用户名
    github_repo_name: str = "daily-papers-site"  # 网站仓库名

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
