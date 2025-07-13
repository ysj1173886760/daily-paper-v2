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

    use_v2_prompt: bool = False

    # LLM论文过滤相关配置
    enable_llm_filter: bool = False  # 是否启用LLM过滤器
    user_interested_content: str = ""  # 用户感兴趣的论文内容描述
    
    # 论文分析模板配置
    analysis_template: str = "v2"  # 分析模板名称，可选值: "v1", "v2"

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
