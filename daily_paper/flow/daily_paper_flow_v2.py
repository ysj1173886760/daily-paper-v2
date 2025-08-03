from pocketflow import Flow
from daily_paper.nodes import (
    FetchPapersNode,
    FilterExistingPapersNode,
    FilterIrrelevantPapersNode,
    ProcessPapersV2Node,
    PushToFeishuNode,
    GenerateHTMLNode,
    PublishRSSNode,
    DeployGitHubNode,
)
from daily_paper.utils.call_llm import init_llm
from daily_paper.utils.feishu_client import init_feishu
from daily_paper.utils.logger import logger
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.config import Config
from daily_paper.templates import get_template


def _create_process_node_with_template(config: Config) -> ProcessPapersV2Node:
    """创建带模板的处理节点，处理模板错误和回退逻辑"""
    try:
        template = get_template(config.analysis_template)
        process_node = ProcessPapersV2Node(template_name=config.analysis_template)
        logger.info(f"使用分析模板: {config.analysis_template} ({template.description})")
        return process_node
    except ValueError as e:
        logger.error(f"模板配置错误: {e}")
        # 回退到默认配置
        process_node = ProcessPapersV2Node(template_name="v2")
        logger.warning("回退到默认V2模板")
        return process_node


def _create_push_node_with_template(config: Config) -> PushToFeishuNode:
    """创建带模板的推送节点，处理模板错误和回退逻辑"""
    try:
        template = get_template(config.analysis_template)
        push_node = PushToFeishuNode(summary_formatter=template.format_to_markdown)
        logger.info(f"使用分析模板: {config.analysis_template} ({template.description})")
        return push_node
    except ValueError as e:
        logger.error(f"模板配置错误: {e}")
        template = get_template("v2")
        push_node = PushToFeishuNode(summary_formatter=template.format_to_markdown)
        logger.warning("回退到默认V2模板")
        return push_node


def _create_rss_nodes(
    config: Config,
) -> tuple[GenerateHTMLNode, PublishRSSNode, DeployGitHubNode]:
    """创建RSS相关节点"""
    custom_tag = getattr(config, "rss_custom_tag", "")
    
    generate_html_node = GenerateHTMLNode(custom_tag=custom_tag)
    publish_rss_node = PublishRSSNode(
        site_url=getattr(
            config, "rss_site_url", "https://your-username.github.io/daily-papers-site"
        ),
        feed_title=getattr(config, "rss_feed_title", "Daily AI Papers"),
        feed_description=getattr(
            config, "rss_feed_description", "Latest papers in AI research"
        ),
        custom_tag=custom_tag,
    )
    deploy_github_node = DeployGitHubNode.create_from_config(config)
    return generate_html_node, publish_rss_node, deploy_github_node


def _create_base_nodes(
    config: Config,
) -> tuple[FetchPapersNode, FilterExistingPapersNode]:
    """创建基础节点（fetch和filter）"""
    fetch_node = FetchPapersNode(
        config.arxiv_topic_list, config.arxiv_search_offset, config.arxiv_search_limit
    )
    filter_node = FilterExistingPapersNode()
    return fetch_node, filter_node


def create_summary_only_flow(config: Config) -> Flow:
    """创建仅进行论文总结的流程（不包含推送）"""
    fetch_node, filter_node = _create_base_nodes(config)
    process_node = _create_process_node_with_template(config)

    # 构建仅总结的流程
    if config.enable_llm_filter:
        llm_filter_node = FilterIrrelevantPapersNode(config)
        fetch_node >> filter_node >> llm_filter_node >> process_node
        logger.info("已启用LLM论文过滤功能")
    else:
        fetch_node >> filter_node >> process_node
        logger.info("未启用LLM论文过滤功能")

    flow = Flow(start=fetch_node)
    logger.info("Summary-only Flow 创建完成")
    return flow

def create_push_feishu_flow(config: Config) -> Flow:
    """创建仅进行飞书推送的流程"""
    push_node = _create_push_node_with_template(config)
    
    flow = Flow(start=push_node)
    logger.info("Feishu-only Flow 创建完成")
    return flow


def create_push_rss_flow(config: Config) -> Flow:
    """创建仅进行RSS发布的流程"""
    generate_html_node, publish_rss_node, deploy_github_node = _create_rss_nodes(config)
    
    # 构建RSS发布流程：generate_html -> publish_rss -> deploy_github
    generate_html_node >> publish_rss_node >> deploy_github_node
    
    flow = Flow(start=generate_html_node)
    logger.info("RSS-only Flow 创建完成")
    return flow


def run_summary_flow(config: Config):
    try:
        shared = {
            "paper_manager": PaperMetaManager(config.meta_file_path),
        }
        
        flow = create_summary_only_flow(config)
        flow.run(shared)

    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}")
        raise

    logger.info(f"原始论文数: {len(shared.get('raw_papers', {}))}")
    logger.info(f"新论文数: {len(shared.get('new_papers', {}))}")
    logger.info(f"处理摘要数: {len(shared.get('summaries', {}))}")

    return shared

def run_push_feishu_flow(config: Config):
    logger.info("开始运行飞书推送流程")
    try:
        shared = {
            "paper_manager": PaperMetaManager(config.meta_file_path),
        }

        flow = create_push_feishu_flow(config)
        flow.run(shared)

    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}")
        raise
    
    logger.info(f"推送成功数: {len(shared.get('push_results', []))}")
    return shared

def run_push_rss_flow(config: Config):
    logger.info("开始运行RSS发布流程")
    try:
        shared = {
            "paper_manager": PaperMetaManager(config.meta_file_path),
        }

        flow = create_push_rss_flow(config)
        flow.run(shared)

    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}")
        raise
    
    return shared

def run_daily_paper_flow_v2(config: Config):
    init_llm(config.llm_base_url, config.llm_api_key, config.llm_model)
    init_feishu(config.feishu_webhook_url)

    run_summary_flow(config)

    if config.enable_feishu_push:
      run_push_feishu_flow(config)

    if config.enable_rss_publish:
      run_push_rss_flow(config)

def reset_push_status_to_false(config: Config):
    paper_manager = PaperMetaManager(config.meta_file_path)

    all_papers = paper_manager.get_all_papers()

    update_dict = {paper_id: {"pushed": False} for paper_id in all_papers["paper_id"]}
    paper_manager.update_papers(update_dict)
    paper_manager.persist()

    logger.info("重置推送状态成功")


# 导出函数
__all__ = [
    "run_daily_paper_flow_v2",
]

if __name__ == "__main__":
    config = Config()
    reset_push_status_to_false(config)
