# FeishuClient 重构指南

## 🎯 重构目标

重构飞书客户端，从全局单一 webhook URL 改为实例化设计，每个客户端可以独立管理自己的 webhook URL，支持多个飞书群组推送。

## 🔄 主要改进

### 1. 实例化设计
**原来（全局方式）:**
```python
from daily_paper.utils.feishu_client import init_feishu, send_paper_to_feishu

# 全局初始化，只能有一个webhook URL
init_feishu("https://webhook-url-1")
send_paper_to_feishu(paper, summary)  # 使用全局URL
```

**现在（实例化）:**
```python
from daily_paper.utils.feishu_client import FeishuClient

# 创建多个客户端实例
client1 = FeishuClient("https://webhook-url-1")  # RAG群组
client2 = FeishuClient("https://webhook-url-2")  # KG群组
client3 = FeishuClient("https://webhook-url-3")  # 测试群组

# 独立推送到不同群组
client1.send_paper(paper, summary)
client2.send_daily_report(report)
client3.send_text("测试消息")
```

### 2. 改进的 API 设计

#### FeishuClient 类方法
- `send_message(message: Dict)` - 发送原始消息（底层方法）
- `send_paper(paper: ArxivPaper, summary: str)` - 发送论文
- `send_daily_report(content: str, title: str)` - 发送日报
- `send_text(text: str)` - 发送纯文本

#### 向后兼容
```python
# 旧的方式仍然有效
from daily_paper.utils.feishu_client import init_feishu, send_paper_to_feishu

init_feishu("https://webhook-url")
send_paper_to_feishu(paper, summary)  # 内部使用默认客户端实例
```

### 3. 错误处理改进

```python
class FeishuClient:
    def send_message(self, message):
        # HTTP 错误处理
        response.raise_for_status()
        
        # 飞书 API 错误检查
        result = response.json()
        if result.get("code") != 0:
            raise ValueError(f"飞书API错误: {result.get('msg')}")
        
        return result
```

## 🚀 使用方式

### 1. 基本用法

```python
from daily_paper.utils.feishu_client import FeishuClient

# 创建客户端
client = FeishuClient("https://open.larkoffice.com/open-apis/bot/v2/hook/xxx")

# 发送文本消息
client.send_text("Hello, 飞书！")

# 发送日报
report_content = "# 今日论文摘要\n\n..."
client.send_daily_report(report_content, "📊 AI论文日报")
```

### 2. 在工作流中使用

```python
from daily_paper.nodes.push_to_feishu_node import PushToFeishuNode
from daily_paper.utils.feishu_client import FeishuClient

# 方式1：传入客户端实例
feishu_client = FeishuClient("https://webhook-url")
push_node = PushToFeishuNode(feishu_client=feishu_client)

# 方式2：从配置自动创建（推荐）
# 节点会自动从 shared["config"] 中读取 feishu_webhook_url 创建客户端
push_node = PushToFeishuNode()  # 配置中需要有 feishu_webhook_url
```

### 3. 多群组推送

```python
# 不同配置文件对应不同群组
rag_config = Config.from_yaml("config/rag.yaml")
kg_config = Config.from_yaml("config/kg.yaml")

rag_client = FeishuClient(rag_config.feishu_webhook_url)
kg_client = FeishuClient(kg_config.feishu_webhook_url)

# 同时推送到两个群组
rag_client.send_daily_report(rag_report, "📊 RAG论文日报")
kg_client.send_daily_report(kg_report, "📊 知识图谱论文日报")
```

## 🔧 节点集成

### PushToFeishuNode
```python
class PushToFeishuNode(Node):
    def __init__(self, feishu_client: FeishuClient = None, **kwargs):
        # 支持传入客户端实例或从配置创建
        
    def prep(self, shared):
        # 优先级：传入的客户端 > 从配置创建 > 错误
        feishu_client = self.feishu_client
        if not feishu_client and config.feishu_webhook_url:
            feishu_client = FeishuClient(config.feishu_webhook_url)
```

### PushDailyReportToFeishuNode
```python
class PushDailyReportToFeishuNode(Node):
    def __init__(self, feishu_client: FeishuClient = None):
        # 支持传入客户端实例或从配置创建
        
    def exec(self, prep_res):
        feishu_client = prep_res["feishu_client"]
        success = feishu_client.send_daily_report(report_content)
```

## 📋 配置文件

现有配置文件无需修改，仍然使用 `feishu_webhook_url` 字段：

```yaml
# config/rag.yaml
feishu_webhook_url: "https://open.larkoffice.com/open-apis/bot/v2/hook/xxx"

# config/kg.yaml  
feishu_webhook_url: "https://open.larkoffice.com/open-apis/bot/v2/hook/yyy"
```

## 🧪 测试

运行测试脚本验证功能：

```bash
# 测试新的 FeishuClient
python test_feishu_client.py

# 测试集成到工作流
python main.py --config_path config/test.yaml --mode publish
```

## ⚡ 性能优化

1. **连接复用**: 每个客户端实例复用 HTTP 连接
2. **重试机制**: 使用 tenacity 实现指数退避重试
3. **错误检查**: 同时检查 HTTP 状态和飞书 API 状态

## 🔄 迁移指南

### 现有代码迁移

**老代码:**
```python
from daily_paper.utils.feishu_client import init_feishu, send_paper_to_feishu

init_feishu(webhook_url)
send_paper_to_feishu(paper, summary)
```

**新代码（推荐）:**
```python
from daily_paper.utils.feishu_client import FeishuClient

client = FeishuClient(webhook_url)
client.send_paper(paper, summary)
```

**或者保持不变（向后兼容）:**
原有代码无需修改，内部自动使用新的客户端实现。

## 🎉 优势总结

- ✅ **多群组支持**: 每个客户端独立管理 webhook URL
- ✅ **向后兼容**: 原有代码无需修改
- ✅ **更好封装**: 面向对象设计，功能更清晰
- ✅ **错误处理**: 改进的错误处理和重试机制
- ✅ **类型安全**: 完整的类型提示
- ✅ **易于测试**: 可以轻松模拟和测试不同场景