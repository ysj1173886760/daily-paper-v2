"""
FetchPapersBulkNode - 使用本地镜像的方式批量获取arXiv论文元数据并做本地筛选

功能概述：
- 通过 arXiv OAI-PMH 接口（ListRecords, metadataPrefix=arXiv, set=cs）增量拉取论文元数据
- 将数据持久化为分区化的 JSONL 文件（按 updated 的 yyyymm 分区）
- 支持在本地根据日期/关键词/分类进行筛选，输出 ArxivPaper 列表
- 不更改现有Flow，按需引入该Node即可

注意：
- 为避免额外依赖，本实现使用 urllib 和 xml.etree 解析XML
- 为便于部署，存储采用 JSONL（每行一个JSON对象），便于增量追加与读取
"""

from __future__ import annotations

import os
import json
import time
import math
import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

import pandas as pd

from pocketflow import Node
from daily_paper.model.arxiv_paper import ArxivPaper
from daily_paper.utils.logger import logger
from daily_paper.config.arxiv_bulk_config import ArxivBulkConfig


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _month_key(d: dt.date) -> str:
    return f"{d.year:04d}{d.month:02d}"


def _arxiv_abs_url(paper_id: str) -> str:
    # 2108.09112v1 -> 2108.09112
    key = paper_id.split("v", 1)[0]
    return f"http://arxiv.org/abs/{key}"


    


class _Checkpoint:
    def __init__(self, path: str):
        self.path = path
        _ensure_dir(os.path.dirname(path))
        self.state: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                self.state = {}

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, self.path)

    def get_since(self) -> Optional[dt.datetime]:
        v = self.state.get("last_updated_iso")
        if not v:
            return None
        try:
            return dt.datetime.fromisoformat(v)
        except Exception:
            return None

    def set_since(self, t: dt.datetime):
        self.state["last_updated_iso"] = t.isoformat()
        self.state["last_run"] = dt.datetime.now().isoformat()
        self.save()


class _OAIClient:
    def __init__(self, endpoint: str, max_retries: int, backoff_base: float, backoff_max: float, jitter: bool):
        self.endpoint = endpoint
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.jitter = jitter

    def _sleep(self, attempt: int):
        delay = min(self.backoff_base ** attempt, self.backoff_max)
        if self.jitter:
            delay *= (1 + 0.1 * (2 * (os.urandom(1)[0] / 255) - 1))
        time.sleep(max(0.5, delay))

    def list_records(self, from_date: dt.date, until_date: dt.date, set_spec: str) -> Iterable[ET.Element]:
        """
        Yield <record> elements for the given window. Handles resumptionToken.
        """
        resumption_token: Optional[str] = None
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "arXiv",
            "set": set_spec,
            "from": from_date.isoformat(),
            "until": until_date.isoformat(),
        }

        while True:
            url = self.endpoint
            query = {}
            if resumption_token:
                query = {"verb": "ListRecords", "resumptionToken": resumption_token}
            else:
                query = params

            attempt = 0
            while True:
                try:
                    full_url = f"{url}?{urlencode(query)}"
                    with urlopen(full_url, timeout=60) as resp:
                        data = resp.read()
                    root = ET.fromstring(data)
                    break
                except (HTTPError, URLError, ET.ParseError) as e:
                    if attempt >= self.max_retries:
                        raise
                    logger.warning(f"OAI request failed (attempt {attempt+1}): {e}")
                    self._sleep(attempt + 1)
                    attempt += 1

            ns = {
                "oai": "http://www.openarchives.org/OAI/2.0/",
                "arxiv": "http://arxiv.org/OAI/arXiv/",
            }
            records = root.findall(".//oai:record", ns)
            for rec in records:
                yield rec

            # resumptionToken handling
            rt_elt = root.find(".//oai:resumptionToken", ns)
            if rt_elt is not None and (rt_elt.text or "").strip():
                resumption_token = (rt_elt.text or "").strip()
                continue
            else:
                break


class _LocalStore:
    """JSONL partitioned store by updated month."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        _ensure_dir(self.base_dir)
        # in-memory cache of per-partition id->updated index
        self._index_cache: Dict[str, Dict[str, str]] = {}

    def _partition_dir(self, yyyymm: str) -> str:
        part_dir = os.path.join(self.base_dir, yyyymm)
        _ensure_dir(part_dir)
        return part_dir

    def _partition_path(self, yyyymm: str) -> str:
        return os.path.join(self._partition_dir(yyyymm), "data.jsonl")

    def _index_path(self, yyyymm: str) -> str:
        return os.path.join(self._partition_dir(yyyymm), "index.json")

    def _load_index(self, yyyymm: str) -> Dict[str, str]:
        if yyyymm in self._index_cache:
            return self._index_cache[yyyymm]
        path = self._index_path(yyyymm)
        index: Dict[str, str] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = {}
        self._index_cache[yyyymm] = index
        return index

    def _save_index(self, yyyymm: str, index: Dict[str, str]):
        path = self._index_path(yyyymm)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False)
        os.replace(tmp, path)

    def append_records(self, rows: List[Dict[str, Any]]):
        """Append records with per-partition dedup by arxiv_id and updated.

        If an id exists with same or newer updated, skip appending.
        Maintains an index.json per partition to avoid re-appending duplicates across runs.
        """
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            updated = r.get("updated")
            try:
                updated_dt = dt.datetime.fromisoformat(updated) if isinstance(updated, str) else updated
            except Exception:
                updated_dt = None
            key = _month_key(updated_dt.date()) if isinstance(updated_dt, dt.datetime) else "unknown"
            buckets.setdefault(key, []).append(r)

        for yyyymm, items in buckets.items():
            path = self._partition_path(yyyymm)
            index = self._load_index(yyyymm)
            appended = 0
            with open(path, "a", encoding="utf-8") as f:
                for obj in items:
                    arxiv_id = obj.get("arxiv_id")
                    updated = obj.get("updated") or ""
                    if not arxiv_id:
                        continue
                    prev = index.get(arxiv_id)
                    # compare ISO timestamps lexicographically (safe for ISO8601)
                    if prev is not None and prev >= updated:
                        continue
                    f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
                    index[arxiv_id] = updated
                    appended += 1
            if appended:
                self._save_index(yyyymm, index)

    def read_range(self, start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
        # Determine months to read
        months = set()
        cur = dt.date(start_date.year, start_date.month, 1)
        end_anchor = dt.date(end_date.year, end_date.month, 1)
        while cur <= end_anchor:
            months.add(_month_key(cur))
            # next month
            ny = cur.year + (1 if cur.month == 12 else 0)
            nm = 1 if cur.month == 12 else cur.month + 1
            cur = dt.date(ny, nm, 1)

        rows: List[Dict[str, Any]] = []
        for m in sorted(months):
            path = os.path.join(self.base_dir, m, "data.jsonl")
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        rows.append(obj)
                    except Exception:
                        pass
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Parse datetimes
        for col in ("created", "updated"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        # Filter by date range (based on updated)
        if "updated" in df.columns:
            mask = (df["updated"].dt.date >= start_date) & (df["updated"].dt.date <= end_date)
            df = df[mask]
        return df


def _parse_record(rec: ET.Element) -> Optional[Dict[str, Any]]:
    ns = {
        "oai": "http://www.openarchives.org/OAI/2.0/",
        "arxiv": "http://arxiv.org/OAI/arXiv/",
    }
    md = rec.find(".//oai:metadata/arxiv:arXiv", ns)
    if md is None:
        return None

    def text(path: str) -> Optional[str]:
        elt = md.find(path, ns)
        return (elt.text or "").strip() if elt is not None and elt.text is not None else None

    # Basic fields
    arxiv_id = text("arxiv:id")
    title = text("arxiv:title") or ""
    abstract = text("arxiv:abstract") or ""
    created = text("arxiv:created")
    updated = text("arxiv:updated") or created
    categories = text("arxiv:categories") or ""
    comments = text("arxiv:comments") or None

    # Authors
    authors = []
    for a in md.findall("arxiv:authors/arxiv:author", ns):
        nm = a.find("arxiv:keyname", ns)
        if nm is None or (nm.text or "").strip() == "":
            nm = a.find("arxiv:name", ns)
        if nm is not None and nm.text:
            authors.append(nm.text.strip())

    # Normalize
    try:
        created_dt = dt.datetime.fromisoformat(created) if created else None
        updated_dt = dt.datetime.fromisoformat(updated) if updated else created_dt
    except Exception:
        created_dt = None
        updated_dt = None

    primary_category = categories.split()[0] if categories else ""

    return {
        "arxiv_id": arxiv_id,
        "title": title.replace("\n", " ").strip(),
        "abstract": abstract.replace("\n", " ").strip(),
        "authors": authors,
        "primary_category": primary_category,
        "categories": categories.split() if categories else [],
        "created": created_dt.isoformat() if created_dt else None,
        "updated": updated_dt.isoformat() if updated_dt else None,
        "comments": comments,
        "url": f"http://arxiv.org/abs/{(arxiv_id or '').split('v',1)[0]}",
        "pdf_url": f"http://arxiv.org/pdf/{(arxiv_id or '').split('v',1)[0]}.pdf",
    }


def _select_locally(df: pd.DataFrame, cfg: ArxivBulkConfig, start_date: dt.date, end_date: dt.date) -> pd.DataFrame:
    if df.empty:
        return df

    # Dedup by arxiv_id, keep latest updated
    if "arxiv_id" in df.columns and "updated" in df.columns:
        df = df.sort_values("updated").drop_duplicates("arxiv_id", keep="last")

    # Keyword filters
    incl = [s.lower() for s in cfg.select_keywords_include]
    excl = [s.lower() for s in cfg.select_keywords_exclude]
    if incl or excl:
        text_series = (df["title"].fillna("") + "\n" + df["abstract"].fillna("")).str.lower()
        if incl:
            mask_incl = text_series.apply(lambda t: any(k in t for k in incl))
        else:
            mask_incl = pd.Series([True] * len(df), index=df.index)
        if excl:
            mask_excl = ~text_series.apply(lambda t: any(k in t for k in excl))
        else:
            mask_excl = pd.Series([True] * len(df), index=df.index)
        df = df[mask_incl & mask_excl]

    # Category filter
    if cfg.select_categories:
        cats = set(cfg.select_categories)
        def has_cat(row):
            if isinstance(row.get("categories"), list):
                return any(c in cats for c in row["categories"])
            pc = row.get("primary_category")
            return pc in cats
        df = df[df.apply(has_cat, axis=1)]

    # Order and limit
    if cfg.select_order_by == "created_desc" and "created" in df.columns:
        df = df.sort_values("created", ascending=False)
    else:
        df = df.sort_values("updated", ascending=False)
    if cfg.select_limit:
        df = df.head(cfg.select_limit)
    return df


class FetchPapersBulkNode(Node):
    """批量/本地模式获取论文元数据并筛选的Node"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _load_cfg(self, shared) -> ArxivBulkConfig:
        config = shared.get("config")
        if config is not None and getattr(config, "arxiv_bulk", None):
            return config.arxiv_bulk
        return ArxivBulkConfig()

    def _determine_date_range(self, cfg: ArxivBulkConfig, shared) -> Tuple[dt.date, dt.date]:
        if cfg.select_date_mode == "range" and cfg.select_start_date and cfg.select_end_date:
            start = dt.date.fromisoformat(cfg.select_start_date)
            end = dt.date.fromisoformat(cfg.select_end_date)
            return start, end
        # support last_week (previous 7 days ending yesterday)
        today = dt.date.today()
        yest = today - dt.timedelta(days=1)
        if cfg.select_date_mode == "last_week":
            start = yest - dt.timedelta(days=6)
            return start, yest
        # default: yesterday
        return yest, yest

    def _incremental_sync(self, cfg: ArxivBulkConfig):
        store = _LocalStore(cfg.bulk_output_dir)
        ckpt = _Checkpoint(cfg.bulk_checkpoint_path)
        client = _OAIClient(cfg.oai_endpoint, cfg.bulk_max_retries, cfg.bulk_backoff_base, cfg.bulk_backoff_max, cfg.bulk_jitter)

        since_dt = ckpt.get_since()
        if since_dt is None:
            # Bootstrap start
            # Try to find earliest start from config; default to 2007-01-01
            start = dt.date.fromisoformat("2007-01-01")
        else:
            start = since_dt.date()
        end = dt.date.today()
        if start >= end:
            logger.info("Bulk store up to date; no sync needed")
            return

        logger.info(f"Starting bulk sync: {start} -> {end}")
        cur = start
        last_seen_updated: Optional[dt.datetime] = since_dt
        while cur <= end:
            window_end = min(end, cur + dt.timedelta(days=cfg.bulk_window_days - 1))
            logger.info(f"Harvesting window {cur} .. {window_end}")
            batch: List[Dict[str, Any]] = []
            try:
                for rec in client.list_records(cur, window_end, cfg.primary_set() if hasattr(cfg, 'primary_set') else (cfg.bulk_sets[0] if getattr(cfg, 'bulk_sets', None) else 'cs')):
                    obj = _parse_record(rec)
                    if not obj or not obj.get("arxiv_id"):
                        continue
                    batch.append(obj)
                    # flush periodically
                    if len(batch) >= 500:
                        store.append_records(batch)
                        # track last updated
                        for it in batch:
                            try:
                                ud = dt.datetime.fromisoformat(it.get("updated"))
                                if last_seen_updated is None or ud > last_seen_updated:
                                    last_seen_updated = ud
                            except Exception:
                                pass
                        batch = []
                # flush tail
                if batch:
                    store.append_records(batch)
                    for it in batch:
                        try:
                            ud = dt.datetime.fromisoformat(it.get("updated"))
                            if last_seen_updated is None or ud > last_seen_updated:
                                last_seen_updated = ud
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Harvest window failed {cur}..{window_end}: {e}")
                # proceed to next window (best-effort), or break depending on policy
            cur = window_end + dt.timedelta(days=1)

        if last_seen_updated is None:
            last_seen_updated = dt.datetime.combine(end, dt.time())
        ckpt.set_since(last_seen_updated)
        logger.info(f"Bulk sync completed. last_updated={last_seen_updated}")

    def prep(self, shared):
        cfg = self._load_cfg(shared)
        start_date, end_date = self._determine_date_range(cfg, shared)
        return {"cfg": cfg, "start_date": start_date, "end_date": end_date}

    def exec(self, prep_res):
        cfg: ArxivBulkConfig = prep_res["cfg"]
        start_date: dt.date = prep_res["start_date"]
        end_date: dt.date = prep_res["end_date"]

        # Step 1: incremental sync (best-effort)
        try:
            self._incremental_sync(cfg)
        except Exception as e:
            logger.error(f"Bulk sync encountered errors: {e}. Proceeding with existing local data.")

        # Step 2: local selection
        store = _LocalStore(cfg.bulk_output_dir)
        df = store.read_range(start_date, end_date)
        cfg.normalize_lists()
        df = _select_locally(df, cfg, start_date, end_date)

        # Step 3: build ArxivPaper list
        papers: List[ArxivPaper] = []
        for _, row in df.iterrows():
            try:
                paper_id = str(row.get("arxiv_id") or "")
                paper_title = str(row.get("title") or "")
                paper_url = _arxiv_abs_url(paper_id)
                paper_abstract = str(row.get("abstract") or "")
                authors = row.get("authors")
                if isinstance(authors, list):
                    paper_authors = ", ".join(authors)
                    paper_first_author = authors[0] if authors else ""
                else:
                    paper_authors = str(authors or "")
                    paper_first_author = paper_authors.split(",", 1)[0].strip() if paper_authors else ""
                primary_category = str(row.get("primary_category") or "")
                created = pd.to_datetime(row.get("created"), errors="coerce")
                updated = pd.to_datetime(row.get("updated"), errors="coerce")
                publish_time = (created.date() if not pd.isna(created) else end_date)
                update_time = (updated.date() if not pd.isna(updated) else publish_time)
                comments = row.get("comments")

                papers.append(
                    ArxivPaper(
                        paper_id=paper_id,
                        paper_title=paper_title,
                        paper_url=paper_url,
                        paper_abstract=paper_abstract,
                        paper_authors=paper_authors,
                        paper_first_author=str(paper_first_author),
                        primary_category=primary_category,
                        publish_time=publish_time,
                        update_time=update_time,
                        comments=str(comments) if comments is not None else None,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to build ArxivPaper from row: {e}")

        logger.info(f"Bulk selected {len(papers)} papers from local store")
        return papers

    def post(self, shared, prep_res, exec_res):
        shared["raw_papers"] = exec_res
        return "default"
