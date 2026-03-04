import re
from typing import Tuple

from core.exceptions import GitHubError


def  parse_github_url(url:str) -> Tuple[str, str]:
    """
    解析 GitHub URL 以提取所有者和仓库名称。

    参数:
        url: 各种格式的 GitHub URL

    返回:
        元组（所有者，仓库名称）

    抛出:
        GitHubError: 如果 URL 格式无效
    """
    if not url or not url.strip():
        raise GitHubError("提供的 URL 为空")

    url = url.strip()
    # 处理不同的 URL 格式
    patterns = [
        r"https?://github\.com/([^/]+)/([^/]+)/?",
        r"github\.com/([^/]+)/([^/]+)/?",
        r"^([^/]+)/([^/]+)/?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            owner, repo = match.groups()
            # 清理仓库名称（如果存在 .git 后缀则移除）
            repo = repo.rstrip(".git")
            return owner, repo

    raise GitHubError(f"无效的 GitHub URL 格式：{url}")



def build_github_api_url(owner: str, repo: str, path: str = "", branch: str = "main") -> str:
    """
      为仓库操作构建 GitHub API URL。

      参数:
          owner: 仓库所有者
          repo: 仓库名称
          path: 仓库内的可选路径
          branch: 分支名称（默认：main）

      返回:
          格式化后的 GitHub API URL
      """
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    if path:
        return f"{base_url}/contents/{path.strip('/')}?ref={branch}"
    else:
        return f"{base_url}/git/trees/{branch}?recursive=1"

def build_github_web_url(
    owner: str, repo: str, path: str = "", branch: str = "main"
) -> str:
    """
    为文件构建 GitHub 网页 URL。

    参数:
        owner: 仓库所有者
        repo: 仓库名称
        path: 仓库内的可选路径
        branch: 分支名称（默认：main）

    返回:
        格式化后的 GitHub 网页 URL
    """
    base_url = f"https://github.com/{owner}/{repo}"

    if path:
        return f"{base_url}/blob/{branch}/{path}"
    else:
        return f"{base_url}/tree/{branch}"