from typing import Optional, List, Tuple, Dict

import requests

from core.exceptions import GitHubError, GitHubRepositoryNotFoundError, GitHubRateLimitError, GitHubAuthenticationError
from core.settings import settings
from github.parse import parse_github_url, build_github_api_url


class GitHubClient:
    """带有认证和错误处理的 GitHub API 客户端。"""
    def __init__(self,token: Optional[str] = None):
        self.token = token or settings.github_api_key
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Doc-MCP/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"




    def get_repository_tree(self,
        repo_url: str,
        branch: str = "main",
        file_extensions: Optional[List[str]] = None,
        include_sha: bool = False,
    ) -> Tuple[List[str], str] | Tuple[List[Dict[str, str]], str]:
        """获取仓库文件树，可选按扩展名筛选。"""

        if file_extensions is None:
            file_extensions = [".md", ".mdx"]

        try:
            #获取git所有者，仓库名称
            owner, repo = parse_github_url(repo_url)
            repo_name = f"{owner}/{repo}"
        except Exception as e:
            raise GitHubError(f"无效的仓库 URL：{e}") from e

        api_url = build_github_api_url(owner, repo, branch=branch)

        try:
            response = requests.get(api_url, headers=self.headers,timeout=settings.github_timeout)
            self._handle_response_errors(response, repo_name)
            data = response.json()
            print("===" * 50)
            print(data)
            print("===" * 50)
            filtered_files = []

            for item in data.get("tree", []):
                if item["type"] == "blob":
                    file_path = item["path"]


        except requests.exceptions.Timeout:
            raise GitHubError(f"请求超时，已超过 {settings.github_timeout} 秒") from None
        except requests.exceptions.RequestException as e:
            raise GitHubError(f"网络错误：{str(e)}") from e


    def _handle_response_errors(self,response: requests.Response, repo_name: str) -> None:
        """处理常见的 GitHub API 响应错误。"""
        if response.status_code == 404:
            raise GitHubRepositoryNotFoundError(f"未找到仓库 '{repo_name}'")
        elif response.status_code == 403:
            if "rate limit" in response.text.lower():
                raise GitHubRateLimitError("GitHub API 速率限制已超出")
            else:
                raise GitHubAuthenticationError(
                    "访问被拒绝。请检查令牌权限"
                )
        elif response.status_code != 200:
            raise GitHubError(
                f"GitHub API 错误：{response.status_code} - {response.text}"
            )

github_client = GitHubClient()