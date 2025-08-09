#!/usr/bin/env python3
"""
测试重构后的 FeishuClient
"""

from daily_paper.utils.feishu_client import FeishuClient
from daily_paper.config import Config

def test_feishu_client():
    """测试 FeishuClient 的基本功能"""
    
    # 从配置文件加载
    config = Config.from_yaml("config/test.yaml")
    
    if not config.feishu_webhook_url:
        print("⚠️ 配置文件中没有设置 feishu_webhook_url，跳过测试")
        return
    
    print("🚀 开始测试 FeishuClient...")
    
    # 创建客户端
    client = FeishuClient(config.feishu_webhook_url)
    print(f"✅ 创建飞书客户端成功")
    
    # 测试发送文本消息
    print("\n📝 测试发送文本消息...")
    success = client.send_text("🧪 FeishuClient 重构测试 - 文本消息")
    print(f"结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 测试发送日报
    print("\n📊 测试发送日报...")
    test_report = """# 📊 FeishuClient 测试日报

## 测试概览
- **测试时间**: 2025年8月9日
- **测试项目**: FeishuClient 重构
- **新功能**: 独立客户端实例

## 测试结果
### ✅ 已完成功能
- 创建 FeishuClient 类
- 支持多个 webhook URL
- 向后兼容原有接口
- 集成到现有工作流

### 🔧 技术改进
- **实例化设计**: 每个客户端独立管理 webhook URL
- **错误处理**: 改进的错误处理和重试机制
- **API 响应检查**: 检查飞书 API 返回状态
- **类型安全**: 更好的类型提示

---
*🤖 FeishuClient 重构测试完成*"""
    
    success = client.send_daily_report(test_report, "🧪 FeishuClient 重构测试")
    print(f"结果: {'✅ 成功' if success else '❌ 失败'}")
    
    print("\n🎉 FeishuClient 测试完成！")

if __name__ == "__main__":
    test_feishu_client()