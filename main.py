from daily_paper.utils.logger import logger
import argparse
from daily_paper.flow.daily_paper_flow_v2 import (
    run_daily_paper_flow_v2,
)
from daily_paper.config import Config

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='Daily Paper Processing System')
    parser.add_argument("--config_path", type=str, default="config/rag.yaml", help="配置文件路径")
    args = parser.parse_args()

    try:
        config = Config.from_yaml(args.config_path)
        run_daily_paper_flow_v2(config)
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
