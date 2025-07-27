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
    ):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.rss_file = self.output_dir / "rss.xml"
        self.site_url = site_url.rstrip("/")
        self.feed_title = feed_title
        self.feed_description = feed_description
        self.max_items = max_items

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prep(self, shared):
        """从共享存储获取HTML文件信息"""
        html_files = shared.get("html_files", [])
        generation_date = shared.get("html_generation_date")

        if not html_files:
            logger.warning("没有找到生成的HTML文件")
            return {}

        return {
            "html_files": html_files,
            "date": generation_date,
            "site_url": self.site_url,
        }

    def exec(self, prep_res):
        """生成或更新RSS feed"""
        if not prep_res.get("html_files"):
            logger.warning("没有HTML文件可发布到RSS")
            return {"success": False}

        html_files = prep_res["html_files"]
        date = prep_res["date"]

        try:
            # 创建或加载现有的RSS feed
            fg = self._create_or_load_feed()

            # 为每个HTML文件添加RSS条目
            new_items_added = 0
            for file_info in html_files:
                if self._add_rss_item(fg, file_info, date):
                    new_items_added += 1

            # 限制最大条目数
            self._limit_feed_items(fg)

            # 更新feed元数据
            fg.lastBuildDate(datetime.now(timezone.utc))

            # 保存RSS文件
            self._save_rss_feed(fg)

            logger.info(f"RSS feed更新完成，新增 {new_items_added} 个条目")
            return {
                "success": True,
                "new_items": new_items_added,
                "total_items": len(fg.entry),
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

    def _create_or_load_feed(self) -> FeedGenerator:
        """创建或加载现有的RSS feed"""
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

        # 如果存在旧的RSS文件，尝试加载现有条目
        if self.rss_file.exists():
            try:
                # 注意：feedgen不支持直接解析现有RSS，我们需要手动处理
                # 这里简化处理，只保留基本的feed信息
                logger.info(f"发现现有RSS文件: {self.rss_file}")
            except Exception as e:
                logger.warning(f"加载现有RSS文件失败: {e}，将创建新的feed")

        return fg

    def _add_rss_item(self, fg: FeedGenerator, file_info: Dict, date: datetime) -> bool:
        """为RSS feed添加新条目"""
        try:
            category = file_info["category"]
            filename = file_info["filename"]
            papers_count = file_info["papers_count"]
            url = f"{self.site_url}{file_info['url']}"

            # 生成条目唯一ID
            item_id = f"{self.site_url}/posts/{filename}"

            # 检查是否已存在相同ID的条目
            for entry in fg.entry:
                if entry.id() == item_id:
                    logger.debug(f"条目已存在，跳过: {item_id}")
                    return False

            # 创建新的RSS条目
            fe = fg.add_entry()
            fe.id(item_id)
            fe.title(f"{date.strftime('%Y-%m-%d')} {category} Papers ({papers_count}篇)")
            fe.link(href=url)
            fe.description(f"今日{category}领域精选论文 {papers_count} 篇，包含详细分析和关键洞察。")

            # 生成发布时间（使用当天的中午12点）
            pub_date = datetime.combine(date, datetime.min.time().replace(hour=12))
            pub_date = pub_date.replace(tzinfo=timezone.utc)
            fe.pubDate(pub_date)

            # 添加分类
            fe.category(category)
            fe.category("AI Research")

            # 生成内容摘要（如果有的话）
            content_summary = self._generate_content_summary(file_info, papers_count)
            fe.content(content_summary, type="CDATA")

            logger.debug(f"添加RSS条目: {fe.title()}")
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
        if len(fg.entry) > self.max_items:
            # 按发布时间排序，保留最新的条目
            fg.entry.sort(key=lambda e: e.pubDate(), reverse=True)
            fg.entry = fg.entry[: self.max_items]
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
