from daily_paper.utils.logger import logger
import argparse
from daily_paper.flow.daily_paper_flow_v2 import run_daily_paper_flow_v2
from daily_paper.config import Config

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='Daily Paper Processing System')
    parser.add_argument("--config_path", type=str, default="config/rag.yaml", help="配置文件路径")
    args = parser.parse_args()

    try:
        config = Config.from_yaml(args.config_path)
        
        # 统一使用V2版本的流程（支持模板系统）
        result = run_daily_paper_flow_v2(config)
            
        # 输出执行结果摘要
        logger.info("=== 执行结果摘要 ===")
        logger.info(f"原始论文数: {len(result.get('raw_papers', {}))}")
        logger.info(f"新论文数: {len(result.get('new_papers', {}))}")
        logger.info(f"处理摘要数: {len(result.get('summaries', {}))}")
        logger.info(f"推送成功数: {len(result.get('push_results', []))}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
