下面列出几款常见、活跃、完全开源（MIT／GPL／AGPL 等）的自托管工具，都能满足「Markdown 阅读＋代码高亮」「收藏/星标」「已读/未读」这三项核心需求，并附上简单对比与落地建议，供你挑选。

---

1. Outline  
   • 仓库：github.com/outline/outline（MIT）  
   • 特色：  
     - Markdown 渲染优秀，内置 PrismJS 代码高亮，支持 Mermaid、LaTeX。  
     - 「Starred」功能可收藏文档；侧边栏对未读更新有红点提醒。  
     - 文档层级（Collection→Document）清晰，适合知识库/专栏型内容生产。  
     - 界面简洁，移动端自适应好。  
   • 适用场景：团队协作或多人写作、需要全文搜索与权限管理的知识库。  

2. Wiki.js  
   • 仓库：github.com/requarks/wiki（AGPL-v3）  
   • 特色：  
     - Markdown/WYSIWYG 双编辑器，内置 Highlight.js 代码高亮。  
     - 可开启「Page Rating / Favourites」模块来收藏页面。  
     - 通过「Page Notifications」或自定义 Tag，可把「未读」/「稍后读」流程做成工作流。  
     - 支持 SSO、细粒度权限、版本管理，扩展插件多。  
   • 适用场景：需要门户＋权限＋插件生态的 Wiki/文档门户。  

3. BookStack  
   • 仓库：github.com/BookStackApp/BookStack（MIT）  
   • 特色：  
     - 层级结构「书本→章节→页面」对内容分册管理友好。  
     - Markdown/富文本双模式，PrismJS 高亮。  
     - 页面可「收藏」（Star）、可设置「Shelf」做阅读清单；第三方小插件可显示已读状态。  
   • 适用场景：内容量较大、需要多级分类与读者阅读进度统计的场景。  

4. Wallabag  
   • 仓库：github.com/wallabag/wallabag（MIT）  
   • 特色：  
     - “稍后阅读”型产品，核心就是「已读/未读」「收藏」「标签」。  
     - 对 HTML 文章解析一流；Markdown 可先转 HTML（Pandoc/Markus）再导入，代码块同样高亮。  
     - 支持浏览器扩展、iOS/Android 客户端。  
   • 适用场景：更像「Instapaper/Pocket」的阅读器，若你文章最终发布在网页或 RSS，可直接一键收集。  

5. Miniflux / FreshRSS（RSS 阅读器思路）  
   • Miniflux（PostgreSQL / Go，AGPL-v3）；FreshRSS（PHP，AGPL-v3）。  
   • 特色：  
     - 天生区分「已读/未读」，支持「星标」。  
     - 订阅源内容是 HTML，Markdown 发布后经站点渲染即可正常阅读；Highlight.js 支持代码。  
   • 适用场景：你的产出通过博客/RSS 发布，团队成员用 RSS 模式订阅阅读。  

---

选型建议
1. 若你已把文章当“知识库”管理，且希望多人协作与全文搜索——优先推荐 Outline（上手最快，UI 最现代）。  
2. 若想要 Wiki 式权限/插件生态，可选 Wiki.js；若内容需要“分册”出版感，则选 BookStack。  
3. 如果文章主要是对外发布、成员只想「先存起来再读」——Wallabag 最贴合“阅读器”思路。  
4. 若已有博客/RSS，直接用 Miniflux/FreshRSS 做阅读、星标与未读管理最省事。

部署小贴士
• 上述工具均提供 Docker Compose 示例，几分钟即可跑起来。  
• 代码高亮多用 PrismJS/Highlight.js，若需特定主题或语言支持，可自行修改前端资源。  
• 「未读」状态常与用户账号关联，若只想本地记录，可用匿名模式或给所有成员发统一账号。  
• 收藏/星标字段大多已内置，如需更多元数据（评分/标签），可通过二开数据库字段或插件实现。

这样，你就能在本地或服务器上搭建一个既支持 Markdown＋代码高亮，又能方便标记阅读状态、收藏文章的生产-阅读闭环。祝项目顺利落地!

# RSS

Read file: daily_paper/nodes/generate_daily_report_node.py

Search files...

要把你已经生成好的文章（Markdown 或转换后的 HTML）通过 RSS 订阅给其他人阅读，基本思路就是：  
“把每篇文章封装成 RSS <item> 或 Atom <entry> 节点 → 输出一个 feed.xml（或 rss.xml）文件 → 把文件放到任何能公网访问到的 URL 上”。  
下面给出一套**最简落地方案**与可直接复用的代码示例，帮助你快速把现有流程改造成 “生成-发布-订阅” 模式。

────────────────
一、整体流程示意
────────────────
1. 你的现有 Flow（Fetch→Process→Generate…）生成文章内容（Markdown / HTML）。  
2. 在 Flow 末尾新增一个 `PublishRSSNode`：  
   • 读取最新生成的文章内容、标题、发布时间、永久链接。  
   • 载入（或新建）本地的 `rss.xml` 文件 → 写入新的 `<item>` → 保存。  
3. 把 `rss.xml` 以及文章本身同步到一个可公开访问的静态托管位置，例如：  
   • GitHub Pages（最简单）、Vercel、Netlify、S3、Nginx Server…  
4. 用户/阅读器（Miniflux、FreshRSS、Reeder…）订阅 `https://your-domain/rss.xml`，即可自动收到更新；已读/未读、星标等功能由阅读器侧完成。

────────────────
二、代码实现（可直接拷贝到项目）
────────────────
依赖：`pip install feedgen`（仅 1 个纯 Python 库，零依赖）

```python
# daily_paper/nodes/publish_rss_node.py
from pocketflow import Node
from pathlib import Path
from feedgen.feed import FeedGenerator
import datetime

class PublishRSSNode(Node):

    def prep(self, shared):
        """从 shared 中获取最新文章信息"""
        article = shared.get("latest_article")  # 你在前面节点填充的 dict，如下格式：
        # {
        #   "title": "Today's RAG Papers",
        #   "content": markdown_text,          # Markdown 源
        #   "link": "https://your-domain/posts/2024-07-06.html",
        #   "published": datetime.datetime.now(),
        # }
        return article

    def exec(self, article):
        if not article:
            return False
        # 1) 读取或创建 feed
        rss_path = Path("public/rss.xml")
        fg = FeedGenerator()
        if rss_path.exists():
            fg.load_extension('rss')
            fg.parse_rss(rss_path.read_bytes())  # 读入旧 feed
        else:
            # 第一次创建 feed 基本信息
            fg.id("https://your-domain/") \
              .title("Daily AI Papers") \
              .link(href="https://your-domain/", rel="alternate") \
              .link(href="https://your-domain/rss.xml", rel="self") \
              .language("zh-cn")

        # 2) 写入新条目
        fe = fg.add_entry()
        fe.id(article["link"])
        fe.title(article["title"])
        fe.link(href=article["link"])
        fe.pubDate(article["published"] if isinstance(article["published"], datetime.datetime)
                   else datetime.datetime.combine(article["published"], datetime.time()))
        # 若你想让阅读器直接渲染 Markdown，可在 content:encoded 里放 HTML
        fe.content(article["content"], type="CDATA")  # feedgen 会放进 <content:encoded>

        # 3) 按时间倒序，最多保留最近 100 条
        fg.sort_entries(lambda e: e.pubDate(), reverse=True)
        fg.entry = fg.entry[:100]

        # 4) 保存
        rss_path.parent.mkdir(parents=True, exist_ok=True)
        rss_path.write_bytes(fg.rss_str(pretty=True))
        return True

    def post(self, shared, prep_res, exec_res):
        return "default"
```

然后在 `flow.py` 中把该节点接到末尾：

```python
from daily_paper.nodes import PublishRSSNode  # 新增
# ...
report_node >> PublishRSSNode()
```

────────────────
三、文章文件本身怎么“放出去”？
────────────────
1. **静态站点方式（推荐）**  
   - 每篇文章转成 HTML（如用 `markdown` 库渲染）→ 保存到 `public/posts/xxxx.html`  
   - `rss.xml` 和 `posts/` 目录一并推送到 GitHub Pages 或其它静态托管。  
   - 优点：无需服务器；feed 和页面一次同步。

2. **直接用 Markdown 链接**  
   - 如果阅读器支持渲染 Markdown，`link` 可指向 `raw.githubusercontent.com/.../file.md`。  
   - 但大多数阅读器遇到纯 Markdown 会当成纯文本，不如转成 HTML 体验好。

3. **已有博客系统**  
   - 如果你已经用 Hugo/Hexo/Jekyll 等生成博客，只需把文章 markdown 写入对应 `content` 目录并交给博客构建；RSS 通常由博客自动生成，可跳过发布节点。

────────────────
四、托管 & 自动化发布
────────────────
• **GitHub Actions**：在 main 分支 push 后自动 `gh-pages` 部署；  
  - 工作流大致步骤：`pip install feedgen markdown` → 运行 daily Flow → 把生成的 `public/` 目录推送到 `gh-pages`。  
• **Docker + Nginx**：将 `public/` 目录挂载为静态目录即可。  
• **Miniflux/FreshRSS** 端订阅时只需填写 feed URL；未读/星标都会自动生效。

────────────────
五、常见问题
────────────────
1. **阅读器抓不到更新？**  
   - 确保 `<pubDate>` / `<lastBuildDate>` 随生成时间递增；缓存时间可能达 15 分钟～1 小时。  
2. **Markdown 中代码高亮丢失？**  
   - feed 里塞 HTML 时，预先用 `pygments` 或 `highlight.js` 渲染成带 `<pre><code class="language-python">` 的片段。  
3. **中文乱码**：确保 `rss.xml` 声明 `<?xml version="1.0" encoding="utf-8"?>`（feedgen 自动加入）。

这样，你就能把现有内容生产链一键输出到 RSS，让任何 RSS 阅读器即时订阅、标记已读/未读、收藏。祝发布顺利！