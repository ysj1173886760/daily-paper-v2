from __future__ import annotations

import yaml
from dataclasses import dataclass
from typing import Dict, Optional

from pydantic import BaseModel, root_validator

from daily_paper.config.arxiv_bulk_config import ArxivBulkConfig


@dataclass(frozen=True)
class ResolvedLLMProfile:
    """Concrete LLM配置，包含创建客户端所需的全部字段。"""

    name: str
    base_url: str
    api_key: str
    model: str
    enable_cache: bool = True
    cache_path: str = "data/llm_cache.jsonl"
    cache_ttl_seconds: Optional[int] = None


class LLMProfile(BaseModel):
    """可配置的LLM Profile，允许仅覆盖部分字段。"""

    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    enable_cache: Optional[bool] = None
    cache_path: Optional[str] = None
    cache_ttl_seconds: Optional[int] = None

    def resolve(self, name: str, fallback: "LLMProfile") -> ResolvedLLMProfile:
        """与fallback合并，生成完整配置。"""

        base_profile = fallback if fallback is not None else LLMProfile()

        return ResolvedLLMProfile(
            name=name,
            base_url=(
                self.base_url if self.base_url is not None else base_profile.base_url
            )
            or "",
            api_key=(self.api_key if self.api_key is not None else base_profile.api_key)
            or "",
            model=(self.model if self.model is not None else base_profile.model) or "",
            enable_cache=self.enable_cache
            if self.enable_cache is not None
            else (
                base_profile.enable_cache
                if base_profile.enable_cache is not None
                else True
            ),
            cache_path=(
                self.cache_path
                if self.cache_path is not None
                else (
                    base_profile.cache_path
                    if base_profile.cache_path is not None
                    else "data/llm_cache.jsonl"
                )
            ),
            cache_ttl_seconds=(
                self.cache_ttl_seconds
                if self.cache_ttl_seconds is not None
                else base_profile.cache_ttl_seconds
            ),
        )


class Config(BaseModel):
    arxiv_topic_list: list[str] = []
    arxiv_search_offset: int = 0
    arxiv_search_limit: int = 50

    meta_file_path: str = "data/test.parquet"

    # Search mode for fetching arXiv papers: "api" or "bulk"
    arxiv_search_mode: str = "api"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_profiles: Dict[str, LLMProfile] = {}

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
    daily_summary_continue_on_push_failure: bool = False  # 推送失败时继续处理下一天

    # Bulk arXiv mirror and selection configuration
    arxiv_bulk: ArxivBulkConfig = ArxivBulkConfig()

    @root_validator(pre=True)
    def _ensure_llm_profiles(cls, values: dict) -> dict:
        """在加载配置时，确保存在默认LLM配置并做向后兼容。"""

        profiles = values.get("llm_profiles") or {}

        # 兼容旧字段：llm_base_url/llm_api_key/llm_model
        default_profile_data = {
            "base_url": values.get("llm_base_url", ""),
            "api_key": values.get("llm_api_key", ""),
            "model": values.get("llm_model", ""),
        }

        existing_default = profiles.get("default") or {}
        merged_default = {**default_profile_data, **existing_default}
        profiles["default"] = merged_default

        # 标准化profile格式
        normalized_profiles = {}
        for name, profile in profiles.items():
            if isinstance(profile, LLMProfile):
                normalized_profiles[name] = profile
            elif isinstance(profile, dict):
                normalized_profiles[name] = LLMProfile(**profile)
            else:
                raise TypeError(f"Invalid LLM profile `{name}`: {profile}")

        values["llm_profiles"] = normalized_profiles
        return values

    def get_llm_profile(
        self, name: str = "default", fallback: str = "default"
    ) -> ResolvedLLMProfile:
        """获取指定名称的LLM配置，缺失字段回退到fallback。"""

        if fallback not in self.llm_profiles:
            raise KeyError(f"Fallback LLM profile `{fallback}` is not defined")

        fallback_profile = self.llm_profiles[fallback]
        profile = self.llm_profiles.get(name, LLMProfile())

        if profile is fallback_profile:
            return fallback_profile.resolve(name, fallback_profile)

        return profile.resolve(name, fallback_profile)

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
