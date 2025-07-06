from pocketflow import Flow
from daily_paper.nodes import (
    FetchPapersNode,
    FilterExistingPapersNode,
    ProcessPapersBatchNode,
    PushToFeishuNode,
)
from daily_paper.utils.call_llm import init_llm
from daily_paper.utils.feishu_client import init_feishu
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.config import Config


def create_daily_paper_flow(config: Config) -> Flow:
    fetch_node = FetchPapersNode(
        config.arxiv_topic_list, config.arxiv_search_offset, config.arxiv_search_limit
    )
    filter_node = FilterExistingPapersNode()
    process_node = ProcessPapersBatchNode()
    push_node = PushToFeishuNode()

    fetch_node >> filter_node >> process_node >> push_node

    flow = Flow(start=fetch_node)

    logger.info("Daily Paper Processing Flow 创建完成")
    return flow


def run_daily_paper_flow(config: Config):
    init_llm(config.llm_base_url, config.llm_api_key, config.llm_model)
    init_feishu(config.feishu_webhook_url)

    try:
        shared = {
            "paper_manager": PaperMetaManager(config.meta_file_path),
        }

        flow = create_daily_paper_flow(config)
        flow.run(shared)

        return shared

    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}")
        raise


# 导出函数
__all__ = [
    "create_daily_paper_flow",
    "run_daily_paper_flow",
]
