"""
GitHub Pages部署节点 - 直接推送文件到GitHub Pages仓库
"""

import json
import os
import requests
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
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
        }

    def exec(self, prep_res):
        """通过GitHub API推送文件内容到站点仓库"""
        if len(prep_res.get("html_files")) == 0:
            logger.info("没有HTML文件需要部署")
            return {"success": True, "reason": "No HTML files to deploy"}

        if not self.github_token or not self.repo_owner:
            logger.warning("GitHub配置不完整，跳过部署")
            return {"success": False, "reason": "GitHub configuration incomplete"}

        try:
            # 通过API推送文件到GitHub仓库
            return self._deploy_by_api_push(prep_res)

        except Exception as e:
            logger.error(f"GitHub API部署失败: {str(e)}")
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


    def _deploy_by_api_push(self, prep_res):
        """通过GitHub API批量推送文件到站点仓库"""
        logger.info("开始通过API批量推送文件...")
        
        source_public = Path("public")
        if not source_public.exists():
            raise Exception("源 public 目录不存在")
        
        # 收集需要推送的文件
        files_to_push = []
        
        # 检查RSS文件
        rss_file = source_public / "rss.xml"
        if rss_file.exists():
            content = rss_file.read_text(encoding="utf-8")
            files_to_push.append({
                "path": "public/rss.xml",
                "content": content,
                "type": "rss"
            })
        
        # 批量获取远程文件信息（一次API调用）
        remote_files_info = self._get_remote_files_batch()
        
        # 检查HTML文件
        html_files_info = prep_res.get("html_files", [])
        for file_info in html_files_info:
            filename = file_info["filename"]
            file_path = f"public/posts/{filename}"
            
            # 读取本地文件内容
            local_file = source_public / "posts" / filename
            if local_file.exists():
                content = local_file.read_text(encoding="utf-8")
                
                # 使用批量获取的信息进行内容比较
                if self._should_push_file_batch(file_path, content, remote_files_info):
                    files_to_push.append({
                        "path": file_path,
                        "content": content,
                        "type": "html",
                        "filename": filename
                    })
                else:
                    logger.debug(f"HTML文件内容相同，跳过推送: {filename}")
            else:
                logger.warning(f"本地HTML文件不存在: {filename}")
        
        if not files_to_push:
            logger.info("没有需要推送的文件")
            return {"success": True, "method": "batch_push", "files_count": 0}
        
        # 批量推送文件
        try:
            pushed_count = self._batch_push_files(files_to_push)
            logger.info(f"批量推送完成，共推送 {pushed_count} 个文件")
            return {
                "success": True,
                "method": "batch_push",
                "files_count": pushed_count,
            }
        except Exception as e:
            logger.error(f"批量推送失败: {str(e)}")
            # 回退到单个文件推送
            # return self._fallback_single_push(files_to_push)

            return {
                "success": False,
                "method": "batch_push",
                "files_count": 0,
            }

    def _push_file_to_github(self, file_path: str, content: str):
        """推送单个文件到GitHub仓库"""
        import base64
        
        # 编码文件内容
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        # 获取文件当前SHA（如果存在）
        sha = self._get_file_sha(file_path)
        
        # 构建请求
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
        
        payload = {
            "message": f"Update {file_path} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_encoded,
            "branch": "main"
        }
        
        if sha:
            payload["sha"] = sha
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        response = requests.put(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code not in [200, 201]:
            logger.error(f"推送文件失败 {file_path}: {response.status_code} - {response.text}")
            raise Exception(f"Failed to push {file_path}: {response.status_code}")
        
        logger.debug(f"成功推送文件: {file_path}")

    def _get_file_sha(self, file_path: str) -> str:
        """获取文件的当前SHA值"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("sha")
            return None
        except:
            return None

    def _should_push_file(self, file_path: str, content: str) -> bool:
        """检查文件是否需要推送（基于内容哈希比较）"""
        existing_sha = self._get_file_sha(file_path)
        
        if not existing_sha:
            # 文件不存在，需要推送
            return True
        
        # 计算本地文件的哈希
        import hashlib
        local_hash = hashlib.sha1(f"blob {len(content.encode('utf-8'))}\0{content}".encode('utf-8')).hexdigest()
        
        # 比较哈希值（GitHub SHA通常显示前7位）
        return not existing_sha.startswith(local_hash[:7])

    def _get_remote_files_batch(self) -> dict:
        """批量获取远程文件信息，避免大量单个API请求"""
        try:
            # 获取整个仓库的tree信息（递归获取所有文件）
            base_sha = self._get_latest_commit_sha()
            
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/trees/{base_sha}"
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            # 递归获取所有文件（包括子目录）
            params = {"recursive": "1"}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                tree_data = response.json()
                
                # 构建文件路径到SHA的映射
                files_info = {}
                for item in tree_data.get("tree", []):
                    if item["type"] == "blob":  # 只处理文件，不处理目录
                        files_info[item["path"]] = {
                            "sha": item["sha"],
                            "size": item.get("size", 0)
                        }
                
                logger.info(f"批量获取了 {len(files_info)} 个远程文件信息")
                return files_info
            else:
                logger.warning(f"批量获取远程文件信息失败: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.warning(f"批量获取远程文件信息异常: {str(e)}")
            return {}

    def _should_push_file_batch(self, file_path: str, content: str, remote_files_info: dict) -> bool:
        """使用批量获取的信息检查文件是否需要推送"""
        # 从批量信息中获取文件SHA
        file_info = remote_files_info.get(file_path)
        
        if not file_info:
            # 文件不存在于远程，需要推送
            logger.debug(f"新文件需要推送: {file_path}")
            return True
        
        existing_sha = file_info["sha"]
        
        # 计算本地文件的哈希
        import hashlib
        local_hash = hashlib.sha1(f"blob {len(content.encode('utf-8'))}\0{content}".encode('utf-8')).hexdigest()
        
        # 比较哈希值
        should_push = not existing_sha.startswith(local_hash[:7])
        
        if should_push:
            logger.debug(f"文件内容已更改，需要推送: {file_path}")
        else:
            logger.debug(f"文件内容相同，跳过: {file_path}")
            
        return should_push

    def _batch_push_files(self, files_to_push: list) -> int:
        """使用GitHub Tree API批量推送文件"""
        if not files_to_push:
            return 0
        
        logger.info(f"开始批量推送 {len(files_to_push)} 个文件")
        
        # 1. 获取当前分支的最新commit SHA
        base_sha = self._get_latest_commit_sha()
        
        # 2. 获取当前tree SHA
        base_tree_sha = self._get_tree_sha(base_sha)
        
        # 3. 创建新的tree（包含所有文件变更）
        tree_items = []
        for file_info in files_to_push:
            # 创建blob
            blob_sha = self._create_blob(file_info["content"])
            
            tree_items.append({
                "path": file_info["path"],
                "mode": "100644",  # 普通文件
                "type": "blob",
                "sha": blob_sha
            })
        
        new_tree_sha = self._create_tree(tree_items, base_tree_sha)
        
        # 4. 创建新的commit
        commit_message = f"Batch update {len(files_to_push)} files - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        new_commit_sha = self._create_commit(commit_message, new_tree_sha, base_sha)
        
        # 5. 更新分支引用
        self._update_ref(new_commit_sha)
        
        logger.info(f"批量推送成功，新commit: {new_commit_sha[:7]}")
        return len(files_to_push)

    def _get_latest_commit_sha(self) -> str:
        """获取当前分支最新commit的SHA"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/main"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()["object"]["sha"]
        else:
            raise Exception(f"Failed to get latest commit SHA: {response.status_code}")

    def _get_tree_sha(self, commit_sha: str) -> str:
        """获取指定commit的tree SHA"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/commits/{commit_sha}"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()["tree"]["sha"]
        else:
            raise Exception(f"Failed to get tree SHA: {response.status_code}")

    def _create_blob(self, content: str) -> str:
        """创建blob对象"""
        import base64
        
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/blobs"
        
        payload = {
            "content": base64.b64encode(content.encode('utf-8')).decode('ascii'),
            "encoding": "base64"
        }
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            return response.json()["sha"]
        else:
            raise Exception(f"Failed to create blob: {response.status_code} - {response.text}")

    def _create_tree(self, tree_items: list, base_tree_sha: str) -> str:
        """创建tree对象"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/trees"
        
        payload = {
            "base_tree": base_tree_sha,
            "tree": tree_items
        }
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            return response.json()["sha"]
        else:
            raise Exception(f"Failed to create tree: {response.status_code} - {response.text}")

    def _create_commit(self, message: str, tree_sha: str, parent_sha: str) -> str:
        """创建commit对象"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/commits"
        
        payload = {
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha]
        }
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            return response.json()["sha"]
        else:
            raise Exception(f"Failed to create commit: {response.status_code} - {response.text}")

    def _update_ref(self, commit_sha: str) -> None:
        """更新分支引用"""
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/main"
        
        payload = {
            "sha": commit_sha,
            "force": False
        }
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        
        response = requests.patch(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Failed to update ref: {response.status_code} - {response.text}")

    def _fallback_single_push(self, files_to_push: list) -> dict:
        """回退到单个文件推送模式"""
        logger.info("使用单个文件推送模式")
        pushed_count = 0
        
        for file_info in files_to_push:
            try:
                self._push_file_to_github(file_info["path"], file_info["content"])
                pushed_count += 1
                logger.debug(f"单个推送成功: {file_info['path']}")
            except Exception as e:
                logger.error(f"单个推送失败 {file_info['path']}: {str(e)}")
        
        return {
            "success": True,
            "method": "single_push_fallback",
            "files_count": pushed_count,
        }



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
