import asyncio
import base64
from typing import Optional, List, Tuple, Dict

import aiohttp
import requests
from aiohttp import ClientTimeout

from core.exceptions import GitHubError, GitHubRepositoryNotFoundError, GitHubRateLimitError, GitHubAuthenticationError
from core.settings import settings
from core.types import GitHubFileInfo
from github.parse import parse_github_url, build_github_api_url
from utils.logger_handler import logger


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
            file_extensions = settings.file_extensions

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
            filtered_files = []

            for item in data.get("tree", []):
                if item["type"] == "blob":
                    file_path = item["path"]
                    if any(
                            file_path.lower().endswith(ext.lower())
                            for ext in file_extensions
                    ):
                        if include_sha:
                            file_data = {"path": file_path, "sha": item["sha"]}
                            filtered_files.append(file_data)
                        else:
                            filtered_files.append(file_path)


            ext_str = ", ".join(file_extensions)
            message = f"在 {repo_name}/{branch} 中找到 {len(filtered_files)} 个扩展名为 ({ext_str}) 的文件"
            logger.info(message)
            return filtered_files, message

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



    async def get_multiple_files(self,  repo_url: str,
        file_paths: List[str],
        branch: str = "main",
        max_concurrent: int = None,
    ) -> Tuple[List[GitHubFileInfo], List[str]]:
        """并发获取多个文件。"""
        if max_concurrent is None:
            max_concurrent = settings.github_concurrent_requests

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_single_file(
            file_path: str,
        ) -> Tuple[Optional[GitHubFileInfo], Optional[str]]:
            async with semaphore:
                try:
                    file_info = await self.get_file_content(repo_url, file_path, branch)
                    return file_info, None
                except Exception as e:
                    logger.error(f"获取 {file_path} 失败：{e}")
                    return None, file_path

        # 并发执行所有文件获取任务  [(file_info,file_path),(file_info,file_path)]
        tasks = [fetch_single_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks,return_exceptions=False)

        successful_files = []
        failed_files = []

        for file_info, failed_path in results:
            if file_info:
                successful_files.append(file_info)
            elif failed_path:
                failed_files.append(failed_path)

        logger.info(
            f"成功获取 {len(successful_files)} 个文件，{len(failed_files)} 个失败"
        )
        return successful_files,failed_files


    async def get_file_content(self, repo_url: str, file_path: str, branch: str) -> GitHubFileInfo:
        """异步获取单个文件内容。"""
        try:
            owner, repo = parse_github_url(repo_url)
        except Exception as e:
            raise GitHubError(f"无效的仓库 URL：{e}") from e

        api_url = build_github_api_url(owner, repo, file_path, branch)

        async with aiohttp.ClientSession(
            headers=self.headers,
            timeout=ClientTimeout(total=settings.github_timeout),
        ) as session:
            try:
                async with session.get(api_url) as response:
                    if response.status == 404:
                        raise GitHubRepositoryNotFoundError(
                            f"未找到文件：{file_path}"
                        )
                    elif response.status == 403:
                        raise GitHubRateLimitError("API 速率限制已超出")
                    elif response.status != 200:
                        raise GitHubError(
                            f"HTTP {response.status}：{await response.text()}"
                        )
                    data = await response.json()

                    if isinstance(data, list):
                        raise GitHubError(
                            f"路径 {file_path} 是一个目录，不是文件"
                        )
                    # 解码内容
                    if data.get("encoding") == "base64":
                        try:
                            content_bytes = base64.b64decode(data["content"])
                            content_text = content_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            content_text = content_bytes.decode(
                                "latin-1", errors="ignore"
                            )
                    else:
                        raise GitHubError(
                            f"不支持的编码格式：{data.get('encoding')}"
                        )
                    return GitHubFileInfo(
                        path=file_path,
                        name=data.get("name", ""),
                        sha=data.get("sha", ""),
                        size=data.get("size", 0),
                        url=data.get("html_url", ""),
                        download_url=data.get("download_url", ""),
                        type=data.get("type", "file"),
                        encoding=data.get("encoding", ""),
                        content=content_text,
                    )
            except asyncio.TimeoutError:
                raise GitHubError(
                    f"请求超时，已超过 {settings.github_timeout} 秒"
                ) from None
            except aiohttp.ClientError as e:
                raise GitHubError(f"网络错误：{str(e)}") from e



github_client = GitHubClient()