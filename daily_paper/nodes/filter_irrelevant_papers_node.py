"""
FilterIrrelevantPapersNode - LLM过滤无关论文节点
"""

from daily_paper.utils.logger import logger
from pocketflow import Node
from daily_paper.utils.data_manager import PaperMetaManager
from daily_paper.utils.call_llm import call_llm
from daily_paper.config import Config
import yaml


class FilterIrrelevantPapersNode(Node):
    """LLM过滤无关论文节点"""

    def __init__(self, config: Config, **kwargs):
        """
        初始化过滤节点

        Args:
            config: 配置对象，包含用户感兴趣的内容描述
        """
        super().__init__(**kwargs)
        self.config = config

    def prep(self, shared):
        """从共享存储中读取论文数据"""
        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 获取未被过滤且没有摘要的新论文
        all_papers = paper_manager.get_all_papers()
        new_papers = all_papers.loc[
            (all_papers["summary"].isna()) & (~all_papers["filtered_out"])
        ]

        return new_papers, paper_manager

    def exec(self, prep_res):
        """使用LLM过滤无关论文"""
        new_papers, paper_manager = prep_res

        if new_papers.empty:
            logger.info("没有需要过滤的新论文")
            return {}

        if not self.config.user_interested_content.strip():
            logger.info("用户感兴趣内容为空，跳过LLM过滤")
            return {}

        filter_results = {}

        for index, row in new_papers.iterrows():
            paper_id = row["paper_id"]
            paper_title = row["paper_title"]
            paper_abstract = row["paper_abstract"]

            # 构建LLM过滤prompt
            prompt = f"""
请判断以下论文是否与用户感兴趣的内容相关。

用户感兴趣的内容：
{self.config.user_interested_content}

论文信息：
标题: {paper_title}
摘要: {paper_abstract}

请分析这篇论文是否与用户感兴趣的内容相关，并按照以下格式回答：

```yaml
relevant: true/false  # true表示相关，false表示不相关
reason: |
  简要说明判断理由
```

请确保输出严格按照上述YAML格式。
"""

            try:
                response = call_llm(prompt)

                # 提取YAML部分
                yaml_start = response.find("```yaml")
                yaml_end = response.find("```", yaml_start + 7)

                if yaml_start != -1 and yaml_end != -1:
                    yaml_content = response[yaml_start + 7 : yaml_end].strip()
                    result = yaml.safe_load(yaml_content)

                    is_relevant = result.get("relevant", True)  # 默认相关
                    reason = result.get("reason", "无法解析判断理由")

                    filter_results[paper_id] = {
                        "relevant": is_relevant,
                        "reason": reason,
                    }

                    if is_relevant:
                        logger.info(f"论文 {paper_id} 相关: {reason}")
                    else:
                        logger.info(f"论文 {paper_id} 不相关，将被过滤: {reason}")

                else:
                    logger.warning(f"无法解析LLM返回结果，论文 {paper_id} 默认为相关")
                    filter_results[paper_id] = {
                        "relevant": True,
                        "reason": "LLM返回格式错误，默认相关",
                    }

            except Exception as e:
                logger.error(f"过滤论文 {paper_id} 时发生错误: {str(e)}，默认为相关")
                filter_results[paper_id] = {
                    "relevant": True,
                    "reason": f"过滤时发生错误: {str(e)}",
                }

        relevant_count = sum(
            1 for result in filter_results.values() if result["relevant"]
        )
        total_count = len(filter_results)
        logger.info(f"LLM过滤完成：{total_count}篇论文中有{relevant_count}篇相关")

        return filter_results

    def post(self, shared, prep_res, exec_res):
        """更新论文的过滤状态"""
        if not exec_res:
            logger.info("没有过滤结果需要保存")
            return "default"

        paper_manager: PaperMetaManager = shared.get("paper_manager")

        # 构建更新字典
        update_dict = {}
        for paper_id, result in exec_res.items():
            if not result["relevant"]:
                # 标记为已过滤
                update_dict[paper_id] = {"filtered_out": True}

        if update_dict:
            # 批量更新过滤状态
            paper_manager.update_papers(update_dict)
            paper_manager.persist()

            filtered_count = len(update_dict)
            logger.info(f"标记了{filtered_count}篇论文为已过滤")

        shared["filter_results"] = exec_res
        return "default"
