import logging
import argparse
from daily_paper.flow import run_rag_papers, run_kg_papers

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='Daily Paper Processing System')
    parser.add_argument("--task", type=str, default="", help="任务名称: rag 或 kg")
    args = parser.parse_args()

    try:
        # 根据任务类型执行不同的流程
        if args.task == "rag":
            logging.info("开始执行RAG论文处理流程")
            result = run_rag_papers()
            logging.info("RAG论文处理流程完成")
        elif args.task == "kg":
            logging.info("开始执行知识图谱论文处理流程")
            result = run_kg_papers()
            logging.info("知识图谱论文处理流程完成")
        else:
            logging.error("未知任务类型，请使用 --task rag 或 --task kg")
            return
            
        # 输出执行结果摘要
        logging.info("=== 执行结果摘要 ===")
        logging.info(f"原始论文数: {len(result.get('raw_papers', {}))}")
        logging.info(f"新论文数: {len(result.get('new_papers', {}))}")
        logging.info(f"处理摘要数: {len(result.get('summaries', {}))}")
        logging.info(f"推送成功数: {len(result.get('push_results', []))}")
        logging.info(f"日报推送: {'成功' if result.get('daily_report_sent') else '失败/无日报'}")
        
    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
