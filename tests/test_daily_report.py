#!/usr/bin/env python3
"""
测试日报生成功能

独立的测试脚本，不依赖main.py
"""

import sys
import os
import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_paper.config import Config
from daily_paper.flow.daily_report_flow import run_daily_report_with_config
from daily_paper.utils.call_llm import init_llm
from daily_paper.utils.feishu_client import init_feishu
from daily_paper.utils.logger import logger
from daily_paper.utils.date_helper import get_yesterday_date, format_date_chinese


def main():
    """测试日报功能的主函数"""
    print("🚀 开始测试日报生成功能")
    
    try:
        # 加载配置
        config = Config.from_yaml("config/test.yaml")
        print(f"✓ 配置加载成功")
        
        # 初始化LLM和飞书客户端
        init_llm(config.llm_base_url, config.llm_api_key, config.llm_model)
        init_feishu(config.feishu_webhook_url)
        print(f"✓ LLM和飞书客户端初始化完成")
        
        # 默认使用昨天日期
        target_date = get_yesterday_date()
        print(f"✓ 目标日期: {format_date_chinese(target_date)}")
        
        # 运行日报流程
        print("📊 开始运行日报生成流程...")
        result = run_daily_report_with_config(config, target_date)
        
        # 输出结果统计
        papers = result.get("yesterday_papers", [])
        analysis_result = result.get("analysis_and_recommendations", {})
        push_result = result.get("push_result", {})
        
        print("\n📈 执行结果:")
        print(f"  - 目标日期: {format_date_chinese(target_date)}")
        print(f"  - 论文数量: {len(papers)}")
        
        if papers:
            print(f"  - 论文标题预览:")
            for i, paper in enumerate(papers[:3], 1):  # 只显示前3篇
                print(f"    {i}. {paper.paper_title[:50]}...")
        
        recommendations = analysis_result.get("recommendations", [])
        print(f"  - 推荐数量: {len(recommendations)}")
        
        if recommendations:
            print(f"  - 推荐论文:")
            for i, rec in enumerate(recommendations, 1):
                print(f"    {i}. {rec.get('title', 'N/A')[:40]}...")
        
        # 推送结果
        if push_result.get("success"):
            print(f"  - 推送状态: ✓ 成功推送到飞书")
            if push_result.get("fallback"):
                print(f"    (使用了回退方案)")
        else:
            print(f"  - 推送状态: ✗ 推送失败")
            if "error" in push_result:
                print(f"    错误: {push_result['error']}")
        
        print("\n🎉 测试完成!")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_with_specific_date():
    """使用特定日期测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试日报生成功能')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--config', type=str, default='config/test.yaml', help='配置文件路径')
    args = parser.parse_args()
    
    try:
        # 解析日期
        if args.date:
            from daily_paper.utils.date_helper import parse_date_string
            target_date = parse_date_string(args.date)
        else:
            target_date = get_yesterday_date()
        
        # 加载配置
        config = Config.from_yaml(args.config)
        
        # 初始化服务
        init_llm(config.llm_base_url, config.llm_api_key, config.llm_model)
        init_feishu(config.feishu_webhook_url)
        
        print(f"🎯 测试日期: {format_date_chinese(target_date)}")
        
        # 运行测试
        result = run_daily_report_with_config(config, target_date)
        
        papers_count = len(result.get("yesterday_papers", []))
        push_success = result.get("push_result", {}).get("success", False)
        
        print(f"📊 结果: {papers_count}篇论文，推送{'成功' if push_success else '失败'}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        test_with_specific_date()
    else:
        main()