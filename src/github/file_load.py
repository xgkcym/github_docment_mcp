from typing import Dict, List

from github.client import github_client
from utils.logger_handler import logger


def create_document_from_file_info():
    pass


def discover_repository_files(
    repo_url: str,
    branch: str = "main",
    file_extensions: List[str] = None,
    include_sha: bool = True,
):
    """
    发现 GitHub 仓库中的文件。

    参数:
        repo_url: GitHub 仓库 URL 或 owner/repo 格式
        branch: Git 分支名称
        file_extensions: 要筛选的文件扩展名列表

    返回:
        元组（文件路径列表，状态消息）
    """
    if file_extensions is None:
        file_extensions = ['md','.mdx']
    try:
        return github_client.get_repository_tree(repo_url, branch, file_extensions,include_sha=include_sha)
    except Exception as e:
        logger.error(f"发现 {repo_url} 中的文件失败：{e}")
        return [], f"错误：{str(e)}"
def discover_repository_files_with_changes(
    repo_url: str,
    repo_name: str,
    branch: str = "main",
    file_extensions: List[str] = None,) -> Dict[str, any]:
    """
   发现文件并与存储的仓库状态比较变化。

   参数:
       repo_url: GitHub 仓库 URL
       repo_name: 用于比较的仓库名称
       branch: Git 分支名称
       file_extensions: 要筛选的文件扩展名列表

   返回:
       包含文件发现结果和变化检测的字典
   """
    try:
        # 获取带有 SHA 的当前文件
        current_files, message = discover_repository_files(repo_url,branch,file_extensions)
    except Exception as e:
        pass