from pydantic import BaseModel, Field
from typing import List, Optional


class ArxivBulkConfig(BaseModel):
    # Harvest / sync
    oai_endpoint: str = "https://export.arxiv.org/oai2"
    bulk_sets: List[str] = Field(default_factory=lambda: ["cs"])  # use first
    bulk_output_dir: str = "data/cs_meta"
    bulk_checkpoint_path: str = "data/checkpoints/cs_oai.json"
    bulk_window_days: int = 30
    bulk_max_retries: int = 5
    bulk_backoff_base: float = 1.5
    bulk_backoff_max: float = 30.0
    bulk_jitter: bool = True

    # Selection
    select_date_mode: str = "last_week"  # "yesterday" | "range" | "last_week"
    select_start_date: Optional[str] = None  # YYYY-MM-DD when mode=range
    select_end_date: Optional[str] = None
    select_keywords_include: List[str] = Field(default_factory=list)
    select_keywords_exclude: List[str] = Field(default_factory=list)
    select_categories: List[str] = Field(default_factory=list)
    select_limit: int = 500
    select_order_by: str = "updated_desc"  # or "created_desc"

    def primary_set(self) -> str:
        return self.bulk_sets[0] if self.bulk_sets else "cs"

    def normalize_lists(self) -> None:
        """Normalize list-like fields allowing comma-separated strings in YAML."""

        def _normalize(value):
            if value is None:
                return []
            if isinstance(value, str):
                parts = value.split(",")
            else:
                try:
                    parts = list(value)
                except TypeError:
                    parts = [value]
            normalized = []
            for item in parts:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    normalized.append(text)
            return normalized

        self.bulk_sets = _normalize(self.bulk_sets)
        self.select_keywords_include = _normalize(self.select_keywords_include)
        self.select_keywords_exclude = _normalize(self.select_keywords_exclude)
        self.select_categories = _normalize(self.select_categories)
