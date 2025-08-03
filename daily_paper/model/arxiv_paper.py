from pydantic import BaseModel
import datetime


class ArxivPaper(BaseModel):
    paper_id: str
    paper_title: str
    paper_url: str
    paper_abstract: str
    paper_authors: str
    paper_first_author: str
    primary_category: str
    publish_time: datetime.date
    update_time: datetime.date
    comments: str | None = None

    # system internal state
    summary: str | None = None
    pushed: bool = False
    push_rss: bool = False  # 标记是否已推送到RSS
    filtered_out: bool = False  # 标记是否被LLM过滤器过滤掉
    rss_meta: str | None = None  # RSS元信息JSON字符串
