from pocketflow import Flow
from daily_paper.nodes import (
    FetchPapersNode,
    FilterExistingPapersNode,
    FilterIrrelevantPapersNode,
    ProcessPapersV2Node,
    PushToFeishuNode,
)
from daily_paper.utils.call_llm import init_llm
from daily_paper.utils.feishu_client import init_feishu
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.config import Config
from daily_paper.templates import get_template


def create_daily_paper_flow(config: Config) -> Flow:
    fetch_node = FetchPapersNode(
        config.arxiv_topic_list, config.arxiv_search_offset, config.arxiv_search_limit
    )
    filter_node = FilterExistingPapersNode()
    
    # 使用配置中的模板创建处理节点
    try:
        template = get_template(config.analysis_template)
        process_node = ProcessPapersV2Node(template_name=config.analysis_template)
        logger.info(f"使用分析模板: {config.analysis_template} ({template.description})")
        
        # 使用模板的markdown格式化器
        push_node = PushToFeishuNode(summary_formatter=template.format_to_markdown)
    except ValueError as e:
        logger.error(f"模板配置错误: {e}")
        # 回退到默认配置
        process_node = ProcessPapersV2Node(template_name="v2")
        template = get_template("v2")
        push_node = PushToFeishuNode(summary_formatter=template.format_to_markdown)
        logger.warning("回退到默认V2模板")

    # 基础流程：fetch -> filter -> process -> push
    if config.enable_llm_filter:
        # 如果启用LLM过滤，在现有过滤后增加LLM过滤节点
        llm_filter_node = FilterIrrelevantPapersNode(config)
        fetch_node >> filter_node >> llm_filter_node >> process_node >> push_node
        logger.info("已启用LLM论文过滤功能")
    else:
        # 原有流程
        fetch_node >> filter_node >> process_node >> push_node
        logger.info("未启用LLM论文过滤功能")

    flow = Flow(start=fetch_node)

    logger.info("Daily Paper Processing Flow 创建完成")
    return flow


def run_daily_paper_flow_v2(config: Config):
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


def reset_push_status_to_false(config: Config):
    paper_manager = PaperMetaManager(config.meta_file_path)

    all_papers = paper_manager.get_all_papers()

    update_dict = {paper_id: {"pushed": False} for paper_id in all_papers["paper_id"]}
    paper_manager.update_papers(update_dict)
    paper_manager.persist()

    logger.info("重置推送状态成功")


# 导出函数
__all__ = [
    "create_daily_paper_flow",
    "run_daily_paper_flow_v2",
]

if __name__ == "__main__":
    config = Config()
    reset_push_status_to_false(config)
