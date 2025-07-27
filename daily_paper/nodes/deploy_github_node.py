"""
GitHub Pages部署节点 - 触发网站更新
"""

import json
import requests
from typing import Dict, Any
from pocketflow import Node
from daily_paper.utils.logger import logger


class DeployGitHubNode(Node):
    """GitHub Pages部署节点，通过API触发网站更新"""

    def __init__(
        self,
        github_token: str = "",
        repo_owner: str = "",
        repo_name: str = "daily-papers-site",
    ):
        super().__init__()
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    def prep(self, shared):
        """从共享存储获取需要部署的数据"""
        return {
            "html_files": shared.get("html_files", []),
            "date": shared.get("html_generation_date"),
            "rss_published": shared.get("rss_published", False),
            "papers_data": self._prepare_papers_data(shared),
        }

    def exec(self, prep_res):
        """触发GitHub Pages部署"""
        if not prep_res.get("html_files"):
            logger.warning("没有HTML文件需要部署")
            return {"success": False, "reason": "No HTML files to deploy"}

        if not self.github_token or not self.repo_owner:
            logger.warning("GitHub配置不完整，跳过部署")
            return {"success": False, "reason": "GitHub configuration incomplete"}

        try:
            # 调用GitHub API触发repository_dispatch事件
            response = self._trigger_github_deployment(prep_res)

            if response.status_code == 204:
                logger.info("GitHub Pages部署触发成功")
                return {
                    "success": True,
                    "response_code": response.status_code,
                    "files_count": len(prep_res["html_files"]),
                }
            else:
                logger.error(f"GitHub API调用失败，状态码: {response.status_code}")
                return {
                    "success": False,
                    "error": f"API call failed with status {response.status_code}",
                    "response_text": response.text,
                }

        except Exception as e:
            logger.error(f"GitHub部署失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def post(self, shared, prep_res, exec_res):
        """更新共享存储中的部署状态"""
        if exec_res.get("success"):
            shared["github_deployed"] = True
            shared["deployment_time"] = prep_res.get("date")
            logger.info(f"GitHub Pages部署成功，更新了 {exec_res.get('files_count', 0)} 个文件")
        else:
            shared["github_deployed"] = False
            error_msg = exec_res.get("error", exec_res.get("reason", "Unknown error"))
            logger.error(f"GitHub Pages部署失败: {error_msg}")

        return "default"

    def _prepare_papers_data(self, shared) -> Dict[str, Any]:
        """准备论文数据用于传递给网站"""
        html_files = shared.get("html_files", [])
        date = shared.get("html_generation_date")

        # 构造传递给网站的数据结构
        papers_data = {
            "html_files": html_files,
            "date": str(date) if date else None,
            "timestamp": shared.get("rss_items_count", 0),
            "source": "daily-paper-v2",
        }

        return papers_data

    def _trigger_github_deployment(self, prep_res) -> requests.Response:
        """调用GitHub API触发部署"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/dispatches"

        payload = {
            "event_type": "publish_papers",
            "client_payload": prep_res["papers_data"],
        }

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        logger.debug(f"调用GitHub API: {url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response

    def configure_from_config(self, config):
        """从配置对象更新GitHub设置"""
        self.github_token = getattr(config, "github_token", "")
        self.repo_owner = getattr(config, "github_repo_owner", "")
        self.repo_name = getattr(config, "github_repo_name", "daily-papers-site")

        if self.github_token and self.repo_owner:
            logger.info(f"GitHub部署配置已更新: {self.repo_owner}/{self.repo_name}")
        else:
            logger.warning("GitHub部署配置不完整，将跳过部署")

    @classmethod
    def create_from_config(cls, config):
        """从配置创建节点实例"""
        return cls(
            github_token=getattr(config, "github_token", ""),
            repo_owner=getattr(config, "github_repo_owner", ""),
            repo_name=getattr(config, "github_repo_name", "daily-papers-site"),
        )
