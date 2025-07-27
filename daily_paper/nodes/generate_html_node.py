"""
HTML生成节点 - 将论文摘要转换为HTML格式
"""

import os
import markdown
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from pocketflow import Node
from daily_paper.utils.logger import logger
from daily_paper.model.arxiv_paper import ArxivPaper


class GenerateHTMLNode(Node):
    """HTML生成节点，将Markdown摘要转换为HTML格式"""

    def __init__(self, output_dir: str = "public"):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.posts_dir = self.output_dir / "posts"

        # 确保输出目录存在
        self.posts_dir.mkdir(parents=True, exist_ok=True)

    def prep(self, shared):
        """从共享存储获取需要生成HTML的论文数据"""
        # 获取论文管理器
        paper_manager = shared.get("paper_manager")
        if not paper_manager:
            return {}

        # 获取未推送到RSS但有摘要的论文
        papers_with_summaries = paper_manager.get_papers_with_summaries(
            unpushed_rss_only=True
        )

        if papers_with_summaries.empty:
            logger.info("没有找到需要生成HTML的论文")
            return {}

        # 转换为字典格式
        papers_dict = {}
        for _, row in papers_with_summaries.iterrows():
            paper_id = row["paper_id"]
            papers_dict[paper_id] = ArxivPaper(**row.to_dict())

        return {
            "papers": papers_dict,
            "date": datetime.now().date(),
            "template_name": getattr(shared, "template_name", "v2"),
            "paper_manager": paper_manager,
        }

    def exec(self, prep_res):
        """生成HTML页面"""
        if not prep_res.get("papers"):
            logger.warning("没有找到需要生成HTML的论文")
            return {"success": False, "files": []}

        papers = prep_res["papers"]
        date = prep_res["date"]
        template_name = prep_res.get("template_name", "v2")

        generated_files = []

        # 按类别分组论文
        categories = self._group_papers_by_category(papers)

        for category, category_papers in categories.items():
            if not category_papers:
                continue

            # 生成HTML内容
            html_content = self._generate_category_html(
                category_papers, category, date, template_name
            )

            # 生成文件名：YYYY-MM-DD-category.html
            filename = f"{date.strftime('%Y-%m-%d')}-{category.lower()}.html"
            filepath = self.posts_dir / filename

            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            generated_files.append(
                {
                    "category": category,
                    "filename": filename,
                    "filepath": str(filepath),
                    "papers_count": len(category_papers),
                    "url": f"/posts/{filename}",
                }
            )

            logger.info(f"生成HTML文件: {filename} ({len(category_papers)}篇论文)")

        return {"success": True, "files": generated_files, "date": date}

    def post(self, shared, prep_res, exec_res):
        """将生成的HTML信息保存到共享存储，并更新push_rss状态"""
        if exec_res.get("success"):
            shared["html_files"] = exec_res["files"]
            shared["html_generation_date"] = exec_res["date"]

            # 更新已处理论文的push_rss状态
            paper_manager = prep_res.get("paper_manager")
            papers = prep_res.get("papers", {})

            if paper_manager and papers:
                # 批量更新push_rss状态为True
                updates = {paper_id: {"push_rss": True} for paper_id in papers.keys()}
                paper_manager.update_papers(updates)
                logger.info(f"已将 {len(papers)} 篇论文标记为RSS已推送")

            logger.info(f"成功生成 {len(exec_res['files'])} 个HTML文件")
        else:
            shared["html_files"] = []
            logger.warning("HTML生成失败")

        return "default"

    def _group_papers_by_category(
        self, papers: Dict[str, ArxivPaper]
    ) -> Dict[str, list]:
        """按论文类别分组"""
        categories = {}

        for paper_id, paper in papers.items():
            # 根据primary_category确定类别
            category = self._determine_category(paper.primary_category)

            if category not in categories:
                categories[category] = []

            categories[category].append(paper)

        return categories

    def _determine_category(self, primary_category: str) -> str:
        """根据arXiv分类确定论文类别"""
        # 简单的分类映射
        if "cs.AI" in primary_category or "cs.LG" in primary_category:
            return "AI"
        elif "cs.CL" in primary_category:
            return "NLP"
        elif "cs.CV" in primary_category:
            return "CV"
        elif "cs.IR" in primary_category:
            return "IR"
        else:
            return "General"

    def _generate_category_html(
        self, papers: list, category: str, date: datetime, template_name: str
    ) -> str:
        """为特定类别生成HTML内容"""
        # 按更新时间排序
        sorted_papers = sorted(papers, key=lambda p: p.update_time, reverse=True)

        # 生成论文列表HTML
        papers_html = ""
        for i, paper in enumerate(sorted_papers, 1):
            paper_html = self._generate_paper_html(paper, i)
            papers_html += paper_html

        # 生成完整页面
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{date.strftime('%Y-%m-%d')} {category} Papers - Daily AI Papers</title>
    <link rel="stylesheet" href="/assets/style.css">
    <link rel="stylesheet" href="/assets/highlight.css">
    <link rel="alternate" type="application/rss+xml" title="Daily AI Papers" href="/rss.xml">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fafafa;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        header h1 {{
            margin: 0;
            font-size: 2.5rem;
        }}
        header p {{
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }}
        nav {{
            margin-top: 1rem;
        }}
        nav a {{
            color: white;
            text-decoration: none;
            margin: 0 1rem;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            background: rgba(255,255,255,0.2);
        }}
        nav a:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .paper-card {{
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .paper-meta {{
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        .paper-title {{
            font-size: 1.4rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 1rem;
        }}
        .paper-summary {{
            color: #444;
            line-height: 1.7;
        }}
        .paper-summary h2 {{
            color: #667eea;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
        }}
        .paper-summary h3 {{
            color: #555;
            margin-top: 1.5rem;
        }}
        .paper-links {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }}
        .paper-links a {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 0.5rem 1rem;
            text-decoration: none;
            border-radius: 5px;
            margin-right: 1rem;
            font-size: 0.9rem;
        }}
        .paper-links a:hover {{
            background: #5a6fd8;
        }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            color: #666;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Daily AI Papers</h1>
        <p>{date.strftime('%Y年%m月%d日')} - {category} 领域论文汇总</p>
        <nav>
            <a href="/">首页</a>
            <a href="/rss.xml">RSS订阅</a>
            <a href="/about.html">关于</a>
        </nav>
    </header>

    <main>
        <div class="summary-info">
            <p>今日共收录 {len(sorted_papers)} 篇 {category} 领域的优质论文，使用 {template_name.upper()} 模板进行分析。</p>
        </div>

        {papers_html}
    </main>

    <footer>
        <p>Generated by Daily Paper Processing System | Template: {template_name.upper()}</p>
        <p>数据来源: arXiv | 分析引擎: Large Language Model</p>
    </footer>
</body>
</html>"""
        return html_content

    def _generate_paper_html(self, paper: ArxivPaper, index: int) -> str:
        """为单篇论文生成HTML"""
        # 将Markdown摘要转换为HTML
        if paper.summary:
            md = markdown.Markdown(extensions=["codehilite", "fenced_code"])
            summary_html = md.convert(paper.summary)
        else:
            summary_html = "<p>暂无摘要</p>"

        return f"""
        <article class="paper-card">
            <div class="paper-meta">
                <span>论文 #{index}</span> | 
                <span>发布: {paper.publish_time}</span> | 
                <span>更新: {paper.update_time}</span> |
                <span>分类: {paper.primary_category}</span>
            </div>
            
            <h2 class="paper-title">{paper.paper_title}</h2>
            
            <div class="paper-summary">
                {summary_html}
            </div>
            
            <div class="paper-links">
                <a href="{paper.paper_url}" target="_blank">arXiv原文</a>
                <a href="{paper.paper_url.replace('abs', 'pdf')}" target="_blank">PDF下载</a>
            </div>
        </article>
        """
