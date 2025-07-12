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

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return cls(**config)
