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
from daily_paper.utils.data_manager import PaperMetaManager, is_valid_summary



class GenerateHTMLNode(Node):
    """HTML生成节点，将Markdown摘要转换为HTML格式"""

    def __init__(self, output_dir: str = "public", custom_tag: str = ""):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.posts_dir = self.output_dir / "posts"
        self.custom_tag = custom_tag

        # 确保输出目录存在
        self.posts_dir.mkdir(parents=True, exist_ok=True)

    def prep(self, shared):
        paper_manager: PaperMetaManager = shared.get("paper_manager")
        if not paper_manager:
            return {}

        all_papers = paper_manager.get_all_papers()
        to_generate_html_papers = all_papers.loc[
            all_papers["summary"].apply(is_valid_summary)
            & (all_papers["rss_meta"].isna())
            & (~all_papers["filtered_out"])
        ]

        logger.info(f"需要生成HTML的论文数量: {len(to_generate_html_papers)}")

        # 转换为字典格式，包含模板信息
        papers_dict = {}
        for _, row in to_generate_html_papers.iterrows():
            paper_id = row["paper_id"]
            paper_data = row.to_dict()
            papers_dict[paper_id] = {
                "paper": ArxivPaper(**paper_data),
                "template": row.get("template", "v2")  # 获取论文的模板信息
            }

        return {
            "papers": papers_dict,
            "date": datetime.now().date(),
            "paper_manager": paper_manager,
        }

    def exec(self, prep_res):
        """生成HTML页面"""
        papers = prep_res["papers"]
        date = prep_res["date"]

        generated_files = []

        # 为每篇论文生成单独的HTML文件
        for paper_id, paper_info in papers.items():
            paper = paper_info["paper"]
            template_name = paper_info["template"]
            
            # 生成HTML内容
            html_content = self._generate_single_paper_html(paper, date, template_name)

            # 生成文件名：YYYY-MM-DD-paper_id.html (使用update_time确保唯一性)
            update_date = paper.update_time.strftime('%Y-%m-%d')
            safe_paper_id = paper_id.replace("/", "-").replace(":", "-")
            filename = f"{update_date}-{safe_paper_id}.html"
            filepath = self.posts_dir / filename

            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            # 生成RSS元信息
            import json
            rss_meta = {
                "title": paper.paper_title,
                "url": f"/posts/{filename}",
                "description": f"{self.custom_tag or 'AI'} 论文: {paper.paper_title} (模板: {template_name.upper()})",
                "category": self.custom_tag or "AI Research",
                "pub_date": update_date,
                "content": f"<h2>{paper.paper_title}</h2><p>使用{template_name.upper()}模板分析的论文摘要。</p><p><a href=\"{'/posts/' + filename}\">阅读全文</a></p>",
                "filename": filename,
                "template": template_name
            }
            
            generated_files.append(
                {
                    "paper_id": paper_id,
                    "paper_title": paper.paper_title,
                    "filename": filename,
                    "filepath": str(filepath),
                    "url": f"/posts/{filename}",
                    "custom_tag": self.custom_tag,
                    "date": update_date,  # 使用update_time作为日期
                    "template": template_name,
                    "rss_meta": json.dumps(rss_meta, ensure_ascii=False)
                }
            )

            logger.info(f"生成HTML文件: {filename} (论文: {paper.paper_title[:50]}...) 使用模板: {template_name}")

        return {"success": True, "files": generated_files, "date": date}

    def post(self, shared, prep_res, exec_res):
        """将生成的HTML信息保存到共享存储，并更新push_rss状态"""
        if exec_res.get("success"):
            shared["html_files"] = exec_res["files"]
            shared["html_generation_date"] = exec_res["date"]

            # 更新已处理论文的push_rss状态
            paper_manager: PaperMetaManager = prep_res.get("paper_manager")
            papers = prep_res.get("papers", {})

            if paper_manager and papers:
                # 批量更新push_rss状态和rss_meta
                updates = {}
                for file_info in exec_res["files"]:
                    paper_id = file_info["paper_id"]
                    updates[paper_id] = {
                        "rss_meta": file_info["rss_meta"]
                    }
                paper_manager.update_papers(updates)
                paper_manager.persist()

                logger.info(f"已将 {len(papers)} 篇论文标记为RSS已推送并保存RSS元信息")

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
            line-height: 1.8;
            font-size: 1rem;
        }}
        .paper-summary h1 {{
            color: #667eea;
            font-size: 1.4rem;
            margin: 2rem 0 1rem 0;
            padding: 0.8rem 1rem;
            background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
            border-left: 4px solid #667eea;
            border-radius: 0 6px 6px 0;
        }}
        .paper-summary h2 {{
            color: #5a67d8;
            font-size: 1.2rem;
            margin: 1.5rem 0 0.8rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        .paper-summary h3 {{
            color: #4a5568;
            font-size: 1.1rem;
            margin: 1.2rem 0 0.6rem 0;
        }}
        .paper-summary p {{
            margin: 1rem 0;
            text-align: justify;
        }}
        .paper-summary ul, .paper-summary ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}
        .paper-summary li {{
            margin: 0.5rem 0;
            line-height: 1.6;
        }}
        .paper-summary strong {{
            color: #2d3748;
            font-weight: 600;
        }}
        .paper-summary em {{
            color: #4a5568;
            font-style: italic;
        }}
        .paper-summary blockquote {{
            margin: 1.5rem 0;
            padding: 1rem 1.5rem;
            background: #f7fafc;
            border-left: 4px solid #667eea;
            border-radius: 0 6px 6px 0;
        }}
        .paper-summary code {{
            background: #f1f5f9;
            color: #475569;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Fira Code', 'Monaco', 'Consolas', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            border: 1px solid #e2e8f0;
        }}
        .paper-summary pre {{
            background: #0f172a;
            color: #f8fafc;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border: 1px solid #334155;
            position: relative;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .paper-summary pre::before {{
            content: 'Python';
            position: absolute;
            top: 0;
            right: 0;
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            border-radius: 0 8px 0 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .paper-summary pre code {{
            background: none;
            color: inherit;
            padding: 0;
            border: none;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        .paper-summary .codehilite {{
            margin: 1.5rem 0;
        }}
        .paper-summary .codehilite pre {{
            margin: 0;
        }}
        /* 语法高亮颜色 */
        .paper-summary .codehilite .c {{ color: #6b7280; }} /* 注释 */
        .paper-summary .codehilite .k {{ color: #8b5cf6; }} /* 关键字 */
        .paper-summary .codehilite .s {{ color: #10b981; }} /* 字符串 */
        .paper-summary .codehilite .n {{ color: #f8fafc; }} /* 变量名 */
        .paper-summary .codehilite .o {{ color: #f59e0b; }} /* 操作符 */
        .paper-summary .codehilite .p {{ color: #94a3b8; }} /* 标点 */
        .paper-summary .codehilite .m {{ color: #ef4444; }} /* 数字 */
        .paper-summary .codehilite .nf {{ color: #06b6d4; }} /* 函数名 */
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

    def _preprocess_structured_summary(self, summary: str) -> str:
        """预处理结构化摘要，改善YAML格式的显示"""
        # 处理YAML式的结构化内容
        lines = summary.split('\n')
        processed_lines = []
        in_pseudocode = False
        code_lines = []
        
        for line in lines:
            # 检测伪代码部分开始
            if 'pseudocode' in line.lower():
                processed_lines.append(line)
                in_pseudocode = True
                continue
            
            # 如果在伪代码部分，收集代码行
            if in_pseudocode:
                # 检测代码块的结束（下一个主标题）
                if (line.strip() and not line.startswith(' ') and not line.startswith('#') 
                    and not line.startswith('function') and not line.startswith('return')
                    and not line.startswith(' ') and not line.startswith('def')
                    and ':' in line and line.strip().endswith(':')):
                    # 输出收集的代码块
                    if code_lines:
                        processed_lines.append('\n```python')
                        processed_lines.extend(code_lines)
                        processed_lines.append('```\n')
                        code_lines = []
                    in_pseudocode = False
                    # 处理新的标题
                    title = line.strip().replace(':', '')
                    processed_lines.append(f"\n**{title}**\n")
                    continue
                else:
                    # 收集代码行，移除不必要的符号
                    clean_line = line.replace(' |', '').replace('|', '') if '|' in line else line
                    code_lines.append(clean_line)
                    continue
            
            # 非伪代码部分的处理
            # 移除YAML格式的竖线符号
            if '|' in line and line.strip().endswith('|'):
                line = line.replace(' |', '').replace('|', '')
            
            # 改善缩进和格式
            if line.strip().startswith('- '):
                # 列表项保持不变
                processed_lines.append(line)
            elif line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                # 主标题加粗
                title = line.strip().replace(':', '')
                processed_lines.append(f"\n**{title}**\n")
            else:
                processed_lines.append(line)
        
        # 处理文件末尾的代码块
        if code_lines:
            processed_lines.append('\n```python')
            processed_lines.extend(code_lines)
            processed_lines.append('```\n')
        
        return '\n'.join(processed_lines)
    
    def _generate_single_paper_html(self, paper: ArxivPaper, date: datetime, template_name: str) -> str:
        """为单篇论文生成完整的HTML页面"""
        # 将Markdown摘要转换为HTML
        if paper.summary:
            # 预处理structured summary格式
            processed_summary = self._preprocess_structured_summary(paper.summary)
            
            # 使用更完整的markdown扩展
            md = markdown.Markdown(extensions=[
                'extra',          # 包含tables, fenced_code, abbr等
                'codehilite',     # 代码高亮
                'toc',           # 目录生成
                'sane_lists',    # 更好的列表处理
                'nl2br'          # 换行转<br>
            ])
            summary_html = md.convert(processed_summary)
        else:
            summary_html = "<p>暂无摘要</p>"

        # 生成完整页面
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{paper.paper_title} - Daily AI Papers</title>
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
            line-height: 1.8;
            font-size: 1rem;
        }}
        .paper-summary h1 {{
            color: #667eea;
            font-size: 1.4rem;
            margin: 2rem 0 1rem 0;
            padding: 0.8rem 1rem;
            background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
            border-left: 4px solid #667eea;
            border-radius: 0 6px 6px 0;
        }}
        .paper-summary h2 {{
            color: #5a67d8;
            font-size: 1.2rem;
            margin: 1.5rem 0 0.8rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        .paper-summary h3 {{
            color: #4a5568;
            font-size: 1.1rem;
            margin: 1.2rem 0 0.6rem 0;
        }}
        .paper-summary p {{
            margin: 1rem 0;
            text-align: justify;
        }}
        .paper-summary ul, .paper-summary ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}
        .paper-summary li {{
            margin: 0.5rem 0;
            line-height: 1.6;
        }}
        .paper-summary strong {{
            color: #2d3748;
            font-weight: 600;
        }}
        .paper-summary em {{
            color: #4a5568;
            font-style: italic;
        }}
        .paper-summary blockquote {{
            margin: 1.5rem 0;
            padding: 1rem 1.5rem;
            background: #f7fafc;
            border-left: 4px solid #667eea;
            border-radius: 0 6px 6px 0;
        }}
        .paper-summary code {{
            background: #f1f5f9;
            color: #475569;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Fira Code', 'Monaco', 'Consolas', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            border: 1px solid #e2e8f0;
        }}
        .paper-summary pre {{
            background: #0f172a;
            color: #f8fafc;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border: 1px solid #334155;
            position: relative;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .paper-summary pre::before {{
            content: 'Python';
            position: absolute;
            top: 0;
            right: 0;
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            border-radius: 0 8px 0 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .paper-summary pre code {{
            background: none;
            color: inherit;
            padding: 0;
            border: none;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        .paper-summary .codehilite {{
            margin: 1.5rem 0;
        }}
        .paper-summary .codehilite pre {{
            margin: 0;
        }}
        /* 语法高亮颜色 */
        .paper-summary .codehilite .c {{ color: #6b7280; }} /* 注释 */
        .paper-summary .codehilite .k {{ color: #8b5cf6; }} /* 关键字 */
        .paper-summary .codehilite .s {{ color: #10b981; }} /* 字符串 */
        .paper-summary .codehilite .n {{ color: #f8fafc; }} /* 变量名 */
        .paper-summary .codehilite .o {{ color: #f59e0b; }} /* 操作符 */
        .paper-summary .codehilite .p {{ color: #94a3b8; }} /* 标点 */
        .paper-summary .codehilite .m {{ color: #ef4444; }} /* 数字 */
        .paper-summary .codehilite .nf {{ color: #06b6d4; }} /* 函数名 */
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
        <p>{date.strftime('%Y年%m月%d日')} - {self.custom_tag or "AI"} 论文</p>
        <nav>
            <a href="/">首页</a>
            <a href="/rss.xml">RSS订阅</a>
            <a href="/about.html">关于</a>
        </nav>
    </header>

    <main>
        <article class="paper-card">
            <div class="paper-meta">
                <span>发布: {paper.publish_time}</span> | 
                <span>更新: {paper.update_time}</span> |
                <span>分类: {paper.primary_category}</span> |
                <span>arXiv ID: {paper.paper_id}</span>
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
    </main>

    <footer>
        <p>Generated by Daily Paper Processing System | Template: {template_name.upper()}</p>
        <p>数据来源: arXiv | 分析引擎: Large Language Model</p>
    </footer>
</body>
</html>"""
        return html_content
