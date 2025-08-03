"""
RSS发布节点 - 生成和更新RSS feed
"""

import os
import markdown
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from pocketflow import Node
from feedgen.feed import FeedGenerator
from daily_paper.utils.logger import logger
from daily_paper.model.arxiv_paper import ArxivPaper


class PublishRSSNode(Node):
    """RSS发布节点，生成和更新RSS feed"""

    def __init__(
        self,
        output_dir: str = "public",
        site_url: str = "https://your-username.github.io/daily-papers-site",
        feed_title: str = "Daily AI Papers",
        feed_description: str = "Latest papers in AI research - RAG, Knowledge Graph, and more",
        max_items: int = 100,
        custom_tag: str = "",
    ):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.rss_file = self.output_dir / "rss.xml"
        self.site_url = site_url.rstrip("/")
        self.feed_title = feed_title
        self.feed_description = feed_description
        self.max_items = max_items
        self.custom_tag = custom_tag

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prep(self, shared):
        """从共享存储获取HTML文件信息和RSS元数据"""
        html_files = shared.get("html_files", [])
        generation_date = shared.get("html_generation_date")
        paper_manager = shared.get("paper_manager")

        if not html_files:
            logger.warning("没有找到生成的HTML文件")
            return {}

        # 获取所有有RSS元信息的论文（用于增量合并）
        all_rss_papers = []
        if paper_manager:
            all_papers_df = paper_manager.get_all_papers()
            rss_papers_df = all_papers_df[
                (all_papers_df["rss_meta"].notna()) & 
                (all_papers_df["rss_meta"] != "")
            ].copy()
            
            if not rss_papers_df.empty:
                # 按update_time排序，最新的在前
                rss_papers_df = rss_papers_df.sort_values("update_time", ascending=False)
                all_rss_papers = rss_papers_df.to_dict("records")

        return {
            "html_files": html_files,
            "date": generation_date,
            "site_url": self.site_url,
            "all_rss_papers": all_rss_papers,
        }

    def exec(self, prep_res):
        """基于rss_meta增量生成RSS feed"""
        all_rss_papers = prep_res.get("all_rss_papers", [])
        
        if not all_rss_papers:
            logger.warning("没有RSS元信息可发布")
            return {"success": False}

        try:
            # 创建新的RSS feed
            fg = self._create_feed()

            # 基于所有rss_meta生成RSS条目（已按update_time排序）
            total_items_added = 0
            for paper_record in all_rss_papers[:self.max_items]:  # 限制最大条目数
                if self._add_rss_item_from_meta(fg, paper_record):
                    total_items_added += 1

            # 更新feed元数据
            fg.lastBuildDate(datetime.now(timezone.utc))

            # 保存RSS文件
            self._save_rss_feed(fg)

            logger.info(f"RSS feed生成完成，包含 {total_items_added} 个条目")
            return {
                "success": True,
                "new_items": len(prep_res.get("html_files", [])),  # 本次新增的
                "total_items": total_items_added,
                "rss_file": str(self.rss_file),
            }

        except Exception as e:
            logger.error(f"RSS生成失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def post(self, shared, prep_res, exec_res):
        """更新共享存储中的RSS信息"""
        if exec_res.get("success"):
            shared["rss_published"] = True
            shared["rss_file"] = exec_res.get("rss_file")
            shared["rss_items_count"] = exec_res.get("total_items", 0)
            logger.info("RSS发布成功")
        else:
            shared["rss_published"] = False
            logger.error(f"RSS发布失败: {exec_res.get('error', 'Unknown error')}")

        return "default"

    def _create_feed(self) -> FeedGenerator:
        """创建新的RSS feed"""
        fg = FeedGenerator()

        # 设置feed基本信息
        fg.id(self.site_url)
        fg.title(self.feed_title)
        fg.link(href=self.site_url, rel="alternate")
        fg.link(href=f"{self.site_url}/rss.xml", rel="self")
        fg.description(self.feed_description)
        fg.language("zh-cn")
        fg.lastBuildDate(datetime.now(timezone.utc))
        fg.managingEditor("ai-research@example.com (AI Research Team)")
        fg.webMaster("webmaster@example.com (Webmaster)")

        return fg

    def _add_rss_item_from_meta(self, fg: FeedGenerator, paper_record: dict) -> bool:
        """基于rss_meta添加RSS条目"""
        try:
            import json
            
            # 解析RSS元信息
            rss_meta = json.loads(paper_record["rss_meta"])
            paper_id = paper_record["paper_id"]
            update_time = paper_record["update_time"]
            
            # 生成条目唯一ID
            item_id = f"{self.site_url}{rss_meta['url']}"

            # 检查是否已存在相同ID的条目（避免重复）
            for entry in fg.entry():
                if entry.id() == item_id:
                    logger.debug(f"条目已存在，跳过: {item_id}")
                    return False

            # 创建新的RSS条目
            fe = fg.add_entry()
            fe.id(item_id)
            fe.title(rss_meta["title"])
            fe.link(href=f"{self.site_url}{rss_meta['url']}")
            fe.description(rss_meta["description"])

            # 设置发布时间（使用update_time）
            try:
                if isinstance(update_time, str):
                    pub_date = datetime.strptime(update_time, '%Y-%m-%d')
                else:
                    pub_date = datetime.combine(update_time, datetime.min.time())
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            except:
                pub_date = datetime.now(timezone.utc)
            fe.pubDate(pub_date)

            # 添加分类
            fe.category({'term': rss_meta["category"]})
            if rss_meta["category"] != "AI Research":
                fe.category({'term': 'AI Research'})

            # 添加内容
            fe.content(rss_meta["content"], type="CDATA")

            logger.debug(f"添加RSS条目: {rss_meta['title']}")
            return True

        except Exception as e:
            logger.error(f"添加RSS条目失败: {e}")
            return False

    def _add_paper_rss_item(self, fg: FeedGenerator, file_info: Dict) -> bool:
        """为RSS feed添加单篇论文条目"""
        try:
            paper_title = file_info["paper_title"]
            filename = file_info["filename"]
            url = f"{self.site_url}{file_info['url']}"
            
            # 生成条目唯一ID（使用paper_id确保唯一性）
            item_id = f"{self.site_url}/posts/{filename}"

            # 检查是否已存在相同ID的条目
            for entry in fg.entry():
                if entry.id() == item_id:
                    logger.debug(f"条目已存在，跳过: {item_id}")
                    return False

            # 创建新的RSS条目
            fe = fg.add_entry()
            fe.id(item_id)
            fe.title(paper_title)
            fe.link(href=url)
            fe.description(f"{self.custom_tag or 'AI'} 论文: {paper_title}")

            # 生成发布时间
            try:
                pub_date = datetime.strptime(file_info["date"], '%Y-%m-%d')
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            except:
                pub_date = datetime.now(timezone.utc)
            fe.pubDate(pub_date)

            # 添加分类
            if self.custom_tag:
                fe.category({'term': self.custom_tag})
            fe.category({'term': 'AI Research'})

            # 添加论文摘要作为内容（如果有的话）
            content = f"<h2>{paper_title}</h2><p>查看完整的论文分析和摘要。</p><p><a href=\"{url}\">阅读全文</a></p>"
            fe.content(content, type="CDATA")

            logger.debug(f"添加RSS条目: {paper_title}")
            return True

        except Exception as e:
            logger.error(f"添加RSS条目失败: {e}")
            return False

    def _generate_content_summary(self, file_info: Dict, papers_count: int) -> str:
        """生成RSS条目的内容摘要"""
        category = file_info["category"]
        date = file_info.get("date", "今日")

        summary = f"""
<h2>{category} 领域论文汇总</h2>
<p>本期为您精选了 {papers_count} 篇 {category} 领域的优质论文，每篇都经过详细的结构化分析。</p>

<h3>主要内容包括：</h3>
<ul>
    <li>📊 问题定义与研究动机</li>
    <li>🔍 技术方案与创新点</li>
    <li>⚡ 实验验证与结果分析</li>
    <li>💡 应用前景与未来展望</li>
</ul>

<p><a href="{self.site_url}{file_info['url']}">点击查看完整分析</a></p>

<hr>
<p><em>由 Daily Paper Processing System 自动生成 | 数据来源: arXiv</em></p>
"""
        return summary.strip()

    def _limit_feed_items(self, fg: FeedGenerator):
        """限制RSS feed的最大条目数"""
        if len(fg.entry()) > self.max_items:
            # 按发布时间排序，保留最新的条目
            entries = fg.entry()
            entries.sort(key=lambda e: e.pubDate(), reverse=True)
            fg.entry(entries[: self.max_items], replace=True)
            logger.info(f"RSS条目已限制为最新 {self.max_items} 条")

    def _save_rss_feed(self, fg: FeedGenerator):
        """保存RSS feed到文件"""
        try:
            # 生成RSS XML
            rss_str = fg.rss_str(pretty=True)

            # 写入文件
            with open(self.rss_file, "wb") as f:
                f.write(rss_str)

            logger.info(f"RSS文件已保存: {self.rss_file}")

        except Exception as e:
            logger.error(f"保存RSS文件失败: {e}")
            raise

    def configure_from_config(self, config: Dict[str, Any]):
        """从配置中更新RSS设置"""
        rss_config = config.get("rss", {})

        if "site_url" in rss_config:
            self.site_url = rss_config["site_url"].rstrip("/")

        if "title" in rss_config:
            self.feed_title = rss_config["title"]

        if "description" in rss_config:
            self.feed_description = rss_config["description"]

        if "max_items" in rss_config:
            self.max_items = rss_config["max_items"]

        logger.info(f"RSS配置已更新: {self.feed_title} @ {self.site_url}")
